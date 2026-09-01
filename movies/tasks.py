"""
Celery tasks for asynchronous ticket PDF generation and email delivery.

- generate_and_email_ticket: Generates PDF, saves to Booking model,
  and emails the ticket to the user.
- Automatic retry on failure (max 3 retries with exponential backoff).
- The booking flow never waits for email delivery to complete.
"""

import logging
from celery import shared_task
from django.core.mail import EmailMessage
from django.core.files.base import ContentFile
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    name='movies.tasks.generate_and_email_ticket',
)
def generate_and_email_ticket(self, booking_ids, user_id):
    """
    Asynchronous task to generate a PDF ticket and email it to the user.

    Args:
        booking_ids: list of Booking PKs (same transaction group)
        user_id: the User PK
    """
    from django.contrib.auth.models import User
    from movies.models import Booking
    from movies.ticket_utils import generate_ticket_pdf

    try:
        user = User.objects.get(pk=user_id)
        bookings = list(
            Booking.objects.filter(pk__in=booking_ids)
            .select_related('movie', 'theater', 'seat')
            .order_by('seat__seat_number')
        )

        if not bookings:
            logger.warning(f'No bookings found for IDs: {booking_ids}')
            return {'status': 'error', 'message': 'No bookings found'}

        ref_booking = bookings[0]

        # 1. Generate the PDF ticket
        logger.info(f'Generating PDF ticket for booking {ref_booking.booking_id}')
        pdf_buffer = generate_ticket_pdf(bookings, user)
        pdf_content = pdf_buffer.read()

        # 2. Save PDF to the first booking's ticket_pdf field
        filename = f'ticket_{ref_booking.booking_id}.pdf'
        ref_booking.ticket_pdf.save(filename, ContentFile(pdf_content), save=True)

        # Also link the same file path to other bookings in the group
        for b in bookings[1:]:
            b.ticket_pdf = ref_booking.ticket_pdf
            b.save(update_fields=['ticket_pdf'])

        # 3. Send email with PDF attachment
        seat_numbers = ', '.join(b.seat.seat_number for b in bookings)
        subject = f'Your BookMySeat Ticket - {ref_booking.movie.name}'
        body = (
            f'Hi {user.get_full_name() or user.username},\n\n'
            f'Your booking is confirmed! Here are the details:\n\n'
            f'Movie: {ref_booking.movie.name}\n'
            f'Theater: {ref_booking.theater.name} ({ref_booking.theater.city})\n'
            f'Show Time: {ref_booking.theater.time.strftime("%A, %d %B %Y at %I:%M %p")}\n'
            f'Seats: {seat_numbers}\n'
            f'Booking ID: {str(ref_booking.booking_id)[:8].upper()}\n'
            f'Payment Ref: {ref_booking.payment_reference}\n\n'
            f'Your e-ticket is attached as a PDF with a QR code for entry verification. '
            f'Please present it at the cinema entrance.\n\n'
            f'Enjoy the movie!\n'
            f'-- Team BookMySeat'
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email] if user.email else [],
        )

        if user.email:
            email.attach(filename, pdf_content, 'application/pdf')
            email.send(fail_silently=False)
            logger.info(f'Ticket email sent to {user.email} for booking {ref_booking.booking_id}')

        # 4. Mark email as sent
        for b in bookings:
            b.email_sent = True
            b.save(update_fields=['email_sent'])

        return {
            'status': 'success',
            'booking_id': str(ref_booking.booking_id),
            'email_sent_to': user.email or 'no email on file',
        }

    except Exception as exc:
        logger.error(f'Failed to generate/email ticket: {exc}', exc_info=True)
        # Celery will auto-retry based on autoretry_for and retry_backoff
        raise
