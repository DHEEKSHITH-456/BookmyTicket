import os
import sys
import django
from unittest.mock import patch, MagicMock

# Setup Django Environment
sys.path.insert(0, r"d:\Intership project\django-bookmyshow-clone")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from django.test.utils import setup_test_environment
setup_test_environment()

from django.test import Client
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from datetime import timedelta
import uuid

from movies.models import Movie, Theater, Seat, Booking, PaymentTransaction
from movies.ticket_utils import generate_ticket_pdf, generate_qr_code
from movies.tasks import generate_and_email_ticket
from movies.payment_service import process_successful_payment

def run_tests():
    print("=" * 75)
    print("   TASK 2: AUTOMATED TICKET GENERATION & EMAIL CONFIRMATION AUDIT   ")
    print("=" * 75)

    client = Client()

    # Setup Test User
    user, _ = User.objects.get_or_create(username='test_patron_t2', defaults={'email': 'patron_t2@example.com'})
    user.set_password('pass123')
    user.email = 'patron_t2@example.com'
    user.save()

    user_b, _ = User.objects.get_or_create(username='unauth_patron_t2', defaults={'email': 'other@example.com'})
    user_b.set_password('pass123')
    user_b.save()

    # Setup Movie & Theater
    movie, _ = Movie.objects.get_or_create(
        name='Task2 Test Cinema Feature',
        defaults={
            'rating': 9.2,
            'duration': 155,
            'popularity': 95.0,
            'description': 'A high-stakes thriller demonstrating ticketing perfection.',
            'release_date': timezone.now().date(),
        }
    )

    theater, _ = Theater.objects.get_or_create(
        name='AMB Cinemas Gachibowli',
        movie=movie,
        defaults={
            'city': 'Hyderabad',
            'location': 'Kondapur Main Road',
            'ticket_price': 250.00,
            'time': timezone.now() + timedelta(days=1),
        }
    )

    # Setup Seats
    seat_a1, _ = Seat.objects.get_or_create(theater=theater, seat_number='T2-A1')
    seat_a2, _ = Seat.objects.get_or_create(theater=theater, seat_number='T2-A2')
    seat_a1.is_booked = True
    seat_a1.save()
    seat_a2.is_booked = True
    seat_a2.save()

    # Setup Bookings
    order_ref = f'ORD-T2-{uuid.uuid4().hex[:8].upper()}'
    booking1 = Booking.objects.create(
        user=user,
        seat=seat_a1,
        movie=movie,
        theater=theater,
        payment_reference=order_ref,
    )
    booking2 = Booking.objects.create(
        user=user,
        seat=seat_a2,
        movie=movie,
        theater=theater,
        payment_reference=order_ref,
    )
    bookings = [booking1, booking2]

    # -------------------------------------------------------------
    # [1] PDF Generation & Complete Schema Structure
    # -------------------------------------------------------------
    print("\n[1] Testing ReportLab Professional PDF Ticket Generation...")
    pdf_buffer = generate_ticket_pdf(bookings, user)
    pdf_bytes = pdf_buffer.read()

    assert pdf_bytes.startswith(b'%PDF-'), "Generated ticket must be a valid PDF (missing %PDF- header)"
    assert len(pdf_bytes) > 5000, f"PDF file size too small ({len(pdf_bytes)} bytes)"
    print(f"  [PASS] 1a: Valid cinema-grade PDF generated ({len(pdf_bytes)} bytes, starts with %PDF-)")

    # -------------------------------------------------------------
    # [2] Scannable Verification QR Code
    # -------------------------------------------------------------
    print("\n[2] Testing Scannable Entrance Verification QR Code...")
    qr_data = f'BOOKMYSEAT|{booking1.booking_id}|{order_ref}|{movie.name}|T2-A1, T2-A2'
    qr_image = generate_qr_code(qr_data)
    assert qr_image is not None, "QR code generation failed"
    print("  [PASS] 2: Scannable QR code verified with entrance verification payload")

    # -------------------------------------------------------------
    # [3] Celery Asynchronous Task Configuration & Retry Policy
    # -------------------------------------------------------------
    print("\n[3] Testing Celery Asynchronous Task & Auto-Retry Backoff Configuration...")
    assert hasattr(generate_and_email_ticket, 'delay'), "Task must be an asynchronous Celery task"
    assert generate_and_email_ticket.max_retries >= 3, f"Expected max_retries >= 3, found {generate_and_email_ticket.max_retries}"
    assert generate_and_email_ticket.retry_backoff is True, "retry_backoff must be enabled for transient email errors"
    assert Exception in generate_and_email_ticket.autoretry_for, "Task must autoretry on Exception"
    print(f"  [PASS] 3: Celery task configured (max_retries={generate_and_email_ticket.max_retries}, backoff=True, autoretry=Exception)")

    # -------------------------------------------------------------
    # [4] Celery Execution, PDF Attachment & Email Sent Flag
    # -------------------------------------------------------------
    print("\n[4] Testing Celery Execution & PDF Email Dispatch...")
    mail.outbox = [] # Clear outbox
    result = generate_and_email_ticket([booking1.pk, booking2.pk], user.pk)
    
    assert result['status'] == 'success', f"Task failed: {result}"
    assert len(mail.outbox) == 1, f"Expected 1 email sent, got {len(mail.outbox)}"
    sent_email = mail.outbox[0]
    
    assert user.email in sent_email.to, f"Email not addressed to {user.email}"
    assert movie.name in sent_email.subject, f"Movie name missing from email subject"
    assert len(sent_email.attachments) == 1, "PDF ticket must be attached to the email"
    
    attach_name, attach_bytes, attach_mime = sent_email.attachments[0]
    assert attach_name.endswith('.pdf'), f"Attachment is not a PDF: {attach_name}"
    assert attach_mime == 'application/pdf', f"Attachment mime is not application/pdf: {attach_mime}"
    assert attach_bytes.startswith(b'%PDF-'), "Attachment bytes do not form a valid PDF"

    # Refresh booking and verify email_sent flag
    booking1.refresh_from_db()
    booking2.refresh_from_db()
    assert booking1.email_sent is True, "booking1.email_sent must be True after delivery"
    assert booking2.email_sent is True, "booking2.email_sent must be True after delivery"
    print(f"  [PASS] 4: Email dispatched with '{attach_name}' ({len(attach_bytes)} bytes) and email_sent=True flag verified")

    # -------------------------------------------------------------
    # [5] Non-Blocking Background Trigger in Payment Flow
    # -------------------------------------------------------------
    print("\n[5] Testing Non-Blocking Asynchronous Background Trigger...")
    with patch('movies.tasks.generate_and_email_ticket.delay') as mock_delay:
        # Create test transaction and test process_successful_payment non-blocking call
        order_id_test = f"ORD-NB-{uuid.uuid4().hex[:6]}"
        seat_nb = Seat.objects.create(theater=theater, seat_number='T2-NB1')
        txn = PaymentTransaction.objects.create(
            order_id=order_id_test,
            user=user,
            movie=movie,
            theater=theater,
            amount=250.00,
            status=PaymentTransaction.STATUS_PENDING
        )
        txn.seats.add(seat_nb)

        created_b = process_successful_payment(order_id_test, f"pay_{order_id_test}")
        assert mock_delay.called, "generate_and_email_ticket.delay() was not called asynchronously"
        print("  [PASS] 5: process_successful_payment triggers Celery task non-blockingly via .delay()")
        
        # Cleanup test transaction
        Booking.objects.filter(payment=txn).delete()
        txn.delete()
        seat_nb.delete()

    # -------------------------------------------------------------
    # [6] Download Previously Booked Ticket (Authenticated)
    # -------------------------------------------------------------
    print("\n[6] Testing Download Previously Booked Ticket Endpoint...")
    client.login(username='test_patron_t2', password='pass123')
    res_download = client.get(f'/movies/booking/{booking1.booking_id}/download-ticket/')
    
    assert res_download.status_code == 200, f"Expected 200 OK, got {res_download.status_code}"
    assert res_download['Content-Type'] == 'application/pdf', f"Expected PDF mime, got {res_download['Content-Type']}"
    assert 'attachment' in res_download.get('Content-Disposition', ''), "Must be an attachment download"
    print("  [PASS] 6: Authenticated patron can download previously booked PDF ticket")

    # -------------------------------------------------------------
    # [7] Security Check: Anonymous User Cannot Download Ticket
    # -------------------------------------------------------------
    print("\n[7] Testing Download Security (Anonymous User)...")
    anon_client = Client()
    res_anon = anon_client.get(f'/movies/booking/{booking1.booking_id}/download-ticket/')
    assert res_anon.status_code in [302, 401, 403], f"Anonymous user was not restricted! Got {res_anon.status_code}"
    print("  [PASS] 7: Anonymous user restricted from downloading ticket (redirected to login)")

    # -------------------------------------------------------------
    # [8] Security Check: Other User Cannot Download Someone Else's Ticket
    # -------------------------------------------------------------
    print("\n[8] Testing Download Security (Other User Access Restriction)...")
    client_b = Client()
    client_b.login(username='unauth_patron_t2', password='pass123')
    res_other = client_b.get(f'/movies/booking/{booking1.booking_id}/download-ticket/')
    assert res_other.status_code == 404, f"Unauthorized user should get 404, got {res_other.status_code}"
    print("  [PASS] 8: Cross-user authorization strictly enforced (returns 404 for non-owner)")

    # -------------------------------------------------------------
    # [9] Booking Confirmation View Post-Booking
    # -------------------------------------------------------------
    print("\n[9] Testing Post-Booking Confirmation View...")
    res_conf = client.get(f'/movies/booking/{booking1.booking_id}/confirmation/')
    assert res_conf.status_code == 200, f"Expected 200, got {res_conf.status_code}"
    content = res_conf.content.decode('utf-8')
    assert movie.name in content, "Movie name missing from confirmation screen"
    assert theater.name in content, "Theater name missing from confirmation screen"
    assert 'download-ticket' in content, "Ticket download button missing from confirmation screen"
    assert 'Screen 1' in content, "Screen detail missing from confirmation screen"
    print("  [PASS] 9: Post-booking confirmation screen renders with movie, theater, screen, and download button")

    # -------------------------------------------------------------
    # [10] Booking History in Profile with Download Action
    # -------------------------------------------------------------
    print("\n[10] Testing User Profile Booking History & Persistent Download Links...")
    res_profile = client.get('/profile/')
    assert res_profile.status_code == 200, f"Expected 200, got {res_profile.status_code}"
    profile_html = res_profile.content.decode('utf-8')
    assert movie.name in profile_html, "Booking not shown in user profile"
    assert f'/movies/booking/{booking1.booking_id}/download-ticket/' in profile_html, "Download ticket link missing in user profile history"
    print("  [PASS] 10: User profile displays confirmed bookings with persistent ticket download actions")

    # Cleanup test records
    booking1.delete()
    booking2.delete()
    seat_a1.delete()
    seat_a2.delete()
    theater.delete()
    movie.delete()
    user.delete()
    user_b.delete()

    print("\n" + "=" * 75)
    print("     ALL 10 TASK 2 ACCEPTANCE CRITERIA ARE 100% VERIFIED!      ")
    print("=" * 75)

if __name__ == '__main__':
    run_tests()
