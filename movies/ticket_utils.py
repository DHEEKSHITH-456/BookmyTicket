"""
Professional PDF Ticket Generator for BookMySeat.

Generates a cinema-style e-ticket with movie details, theater info,
seat numbers, booking ID, payment reference, and a QR code for
verification at the theater entrance.
"""

import io
import qrcode
from qrcode.image.pil import PilImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_qr_code(data, size=35 * mm):
    """Generate a QR code image and return a ReportLab Image object."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
        image_factory=PilImage,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return Image(buffer, width=size, height=size)


def generate_ticket_pdf(bookings, user):
    """
    Generate a professional PDF ticket for a group of bookings
    (same movie, theater, showtime — multiple seats).

    Args:
        bookings: list of Booking objects (all for same transaction)
        user: the User who made the booking

    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = io.BytesIO()

    ref_booking = bookings[0]
    movie = ref_booking.movie
    theater = ref_booking.theater
    seat_numbers = ', '.join(b.seat.seat_number for b in bookings)
    booking_id = str(ref_booking.booking_id)
    payment_ref = ref_booking.payment_reference
    total_price = theater.ticket_price * len(bookings)

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    style_header = ParagraphStyle(
        'TicketHeader', parent=styles['Heading1'],
        fontSize=22, textColor=colors.HexColor('#F84464'),
        alignment=TA_CENTER, spaceAfter=2 * mm, fontName='Helvetica-Bold',
    )
    style_sub = ParagraphStyle(
        'SubHeader', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER, spaceAfter=6 * mm,
    )
    style_section = ParagraphStyle(
        'SectionHeader', parent=styles['Heading2'],
        fontSize=13, textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=3 * mm, fontName='Helvetica-Bold',
    )
    style_label = ParagraphStyle(
        'Label', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#888888'), fontName='Helvetica',
    )
    style_value = ParagraphStyle(
        'Value', parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#1a1a2e'), fontName='Helvetica-Bold',
    )
    style_footer = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=7, textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER, spaceAfter=2 * mm,
    )

    elements = []

    # --- HEADER ---
    elements.append(Paragraph('BookMySeat', style_header))
    elements.append(Paragraph('Your E-Ticket — Present this at the entrance', style_sub))

    divider_data = [[''] * 1]
    divider = Table(divider_data, colWidths=[doc.width])
    divider.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#F84464')),
    ]))
    elements.append(divider)
    elements.append(Spacer(1, 6 * mm))

    # --- MOVIE DETAILS ---
    elements.append(Paragraph('MOVIE DETAILS', style_section))
    genres_str = ', '.join(g.name for g in movie.genres.all()) if movie.genres.exists() else 'N/A'
    languages_str = ', '.join(l.name for l in movie.languages.all()) if movie.languages.exists() else 'N/A'
    movie_data = [
        [Paragraph('Movie', style_label), Paragraph(movie.name, style_value)],
        [Paragraph('Genre', style_label), Paragraph(genres_str, style_value)],
        [Paragraph('Language', style_label), Paragraph(languages_str, style_value)],
        [Paragraph('Duration', style_label), Paragraph(f'{movie.duration} minutes', style_value)],
        [Paragraph('Rating', style_label), Paragraph(f'★ {movie.rating}/10', style_value)],
    ]
    movie_table = Table(movie_data, colWidths=[3.5 * cm, doc.width - 3.5 * cm])
    movie_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#eeeeee')),
    ]))
    elements.append(movie_table)
    elements.append(Spacer(1, 6 * mm))

    # --- THEATER & SHOWTIME ---
    elements.append(Paragraph('THEATER &amp; SHOWTIME', style_section))
    show_date = theater.time.strftime('%A, %d %B %Y')
    show_time = theater.time.strftime('%I:%M %p')
    screen_name = getattr(theater, 'screen', None) or 'Screen 1 (Audi 1 - Dolby Atmos)'
    theater_data = [
        [Paragraph('Theater', style_label), Paragraph(theater.name, style_value)],
        [Paragraph('Screen', style_label), Paragraph(screen_name, style_value)],
        [Paragraph('City', style_label), Paragraph(theater.city, style_value)],
        [Paragraph('Location', style_label), Paragraph(theater.location or theater.city, style_value)],
        [Paragraph('Show Date', style_label), Paragraph(show_date, style_value)],
        [Paragraph('Show Time', style_label), Paragraph(show_time, style_value)],
    ]
    theater_table = Table(theater_data, colWidths=[3.5 * cm, doc.width - 3.5 * cm])
    theater_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#eeeeee')),
    ]))
    elements.append(theater_table)
    elements.append(Spacer(1, 6 * mm))

    # --- BOOKING INFO + QR CODE ---
    elements.append(Paragraph('BOOKING INFORMATION', style_section))
    qr_data = f'BOOKMYSEAT|{booking_id}|{payment_ref}|{movie.name}|{theater.name}|{screen_name}|{seat_numbers}'
    qr_image = generate_qr_code(qr_data, size=30 * mm)

    booking_info_data = [
        [Paragraph('Booking ID', style_label), Paragraph(booking_id[:8].upper(), style_value)],
        [Paragraph('Payment Ref', style_label), Paragraph(payment_ref, style_value)],
        [Paragraph('Seats', style_label), Paragraph(seat_numbers, style_value)],
        [Paragraph('Screen', style_label), Paragraph(screen_name, style_value)],
        [Paragraph('No. of Tickets', style_label), Paragraph(str(len(bookings)), style_value)],
        [Paragraph('Price / Seat', style_label), Paragraph(f'₹{theater.ticket_price}', style_value)],
        [Paragraph('Total Amount', style_label), Paragraph(f'₹{total_price}', style_value)],
    ]
    booking_table = Table(booking_info_data, colWidths=[3.5 * cm, doc.width - 3.5 * cm - 35 * mm])
    booking_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#eeeeee')),
    ]))
    combined_data = [[booking_table, qr_image]]
    combined_table = Table(combined_data, colWidths=[doc.width - 35 * mm, 35 * mm])
    combined_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
    ]))
    elements.append(combined_table)
    elements.append(Spacer(1, 6 * mm))

    # --- PATRON INFO ---
    elements.append(Paragraph('PATRON DETAILS', style_section))
    patron_data = [
        [Paragraph('Name', style_label), Paragraph(user.get_full_name() or user.username, style_value)],
        [Paragraph('Email', style_label), Paragraph(user.email or 'Not provided', style_value)],
        [Paragraph('Booked At', style_label), Paragraph(
            ref_booking.booked_at.strftime('%d %b %Y, %I:%M %p') if ref_booking.booked_at else 'Just now',
            style_value
        )],
    ]
    patron_table = Table(patron_data, colWidths=[3.5 * cm, doc.width - 3.5 * cm])
    patron_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#eeeeee')),
    ]))
    elements.append(patron_table)
    elements.append(Spacer(1, 8 * mm))

    elements.append(divider)
    elements.append(Spacer(1, 4 * mm))

    # --- TERMS & FOOTER ---
    terms = [
        'Please arrive at least 15 minutes before the show time.',
        'This e-ticket is valid for a single entry only.',
        'Carry a valid government-issued photo ID for verification.',
        'Outside food and beverages are not permitted.',
        'This ticket is non-transferable and non-refundable.',
    ]
    for i, term in enumerate(terms, 1):
        elements.append(Paragraph(f'{i}. {term}', style_footer))

    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        'Generated by BookMySeat — Your Premier Movie Ticket Booking Platform', style_footer
    ))
    elements.append(Paragraph(
        f'Booking ID: {booking_id} | Verify at any BookMySeat kiosk', style_footer
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
