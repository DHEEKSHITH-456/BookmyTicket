import os
import sys
import django
import uuid

sys.path.append(os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from movies.models import Movie, Theater, Seat, Booking, PaymentTransaction
from movies.payment_service import generate_mock_signature


def run_comprehensive_e2e_test():
    print("=" * 70)
    print("STARTING COMPREHENSIVE END-TO-END VERIFICATION OF ALL FEATURES")
    print("=" * 70)

    client = Client()

    # ─────────────────────────────────────────────────────────────
    # 1. HOME PAGE VERIFICATION
    # ─────────────────────────────────────────────────────────────
    print("\n[1] Testing Home Page Rendering & Movie Links...")
    resp = client.get('/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    content = resp.content.decode('utf-8')
    assert "BookMySeat" in content, "Brand title not found"
    assert "Book Tickets" in content, "Book Tickets buttons missing"
    assert "Recommended" in content or "Movies" in content
    print("  [OK] Home page renders properly with movies and recommendation feed.")

    # ─────────────────────────────────────────────────────────────
    # 2. REGISTRATION FLOW
    # ─────────────────────────────────────────────────────────────
    print("\n[2] Testing User Registration Flow...")
    unique_user = f"user_{uuid.uuid4().hex[:8]}"
    email = f"{unique_user}@example.com"
    reg_data = {
        'username': unique_user,
        'email': email,
        'password1': 'StrongPassword123!',
        'password2': 'StrongPassword123!',
    }
    resp = client.post('/register/', reg_data)
    assert resp.status_code == 302, f"Expected redirect after registration, got {resp.status_code}"
    assert '/profile/' in resp.url

    created_user = User.objects.filter(username=unique_user).first()
    assert created_user is not None, "User was not created in the database"
    assert created_user.email == email
    print(f"  [OK] User '{unique_user}' registered successfully and auto-logged in to profile.")

    # ─────────────────────────────────────────────────────────────
    # 3. LOGOUT FLOW (POST & GET)
    # ─────────────────────────────────────────────────────────────
    print("\n[3] Testing Logout Flow...")
    # Test POST logout
    resp = client.post('/logout/')
    assert resp.status_code == 302
    assert resp.url == '/'
    # Verify anonymous now
    resp_prof = client.get('/profile/')
    assert resp_prof.status_code == 302, "Expected redirect to login when unauthenticated"
    assert '/login' in resp_prof.url

    # Log back in and test GET logout
    client.login(username=unique_user, password='StrongPassword123!')
    resp = client.get('/logout/')
    assert resp.status_code == 302
    assert resp.url == '/'
    resp_prof = client.get('/profile/')
    assert resp_prof.status_code == 302
    print("  [OK] Both POST and GET logout work cleanly and clear user session.")

    # ─────────────────────────────────────────────────────────────
    # 4. LOGIN FLOW (VALID & INVALID, USERNAME & EMAIL)
    # ─────────────────────────────────────────────────────────────
    print("\n[4] Testing Login Flow (Invalid, Username, and Email)...")
    # Sub-test 4a: Invalid credentials
    resp_bad = client.post('/login/', {'username': unique_user, 'password': 'WrongPassword999!'})
    assert resp_bad.status_code == 200
    assert "Invalid username/email or password" in resp_bad.content.decode('utf-8')
    print("  [OK] Sub-test 4a: Invalid password rejected with clear alert message.")

    # Sub-test 4b: Login with Username
    resp_login_user = client.post('/login/', {'username': unique_user, 'password': 'StrongPassword123!'})
    assert resp_login_user.status_code == 302, f"Login failed for username, got {resp_login_user.status_code}"
    print("  [OK] Sub-test 4b: Login with username succeeds.")

    # Logout
    client.get('/logout/')

    # Sub-test 4c: Login with Email
    resp_login_email = client.post('/login/', {'username': email, 'password': 'StrongPassword123!'})
    assert resp_login_email.status_code == 302, f"Login failed for email, got {resp_login_email.status_code}"
    print("  [OK] Sub-test 4c: Login with email address succeeds.")

    # ─────────────────────────────────────────────────────────────
    # 5. PROFILE PAGE & PROFILE UPDATE
    # ─────────────────────────────────────────────────────────────
    print("\n[5] Testing Profile Page View and Edit...")
    resp_prof = client.get('/profile/')
    assert resp_prof.status_code == 200
    prof_content = resp_prof.content.decode('utf-8')
    assert unique_user in prof_content
    assert "Change Password" in prof_content
    assert "Confirmed Bookings" in prof_content
    assert "Payment Transactions" in prof_content

    # Update profile details
    new_email = f"updated_{email}"
    resp_update = client.post('/profile/', {
        'username': unique_user,
        'email': new_email,
    })
    assert resp_update.status_code == 302
    created_user.refresh_from_db()
    assert created_user.email == new_email
    print("  [OK] Profile displays user ledger and allows updating profile details.")

    # ─────────────────────────────────────────────────────────────
    # 6. CHANGE PASSWORD FLOW
    # ─────────────────────────────────────────────────────────────
    print("\n[6] Testing Change Password Flow...")
    resp_pw_page = client.get('/reset-password/')
    assert resp_pw_page.status_code == 200
    assert "Reset Password" in resp_pw_page.content.decode('utf-8') or "Password" in resp_pw_page.content.decode('utf-8')

    new_password = 'BrandNewPassword456!'
    resp_change = client.post('/reset-password/', {
        'old_password': 'StrongPassword123!',
        'new_password1': new_password,
        'new_password2': new_password,
    })
    assert resp_change.status_code == 302, f"Password change failed, got {resp_change.status_code}"
    assert '/profile/' in resp_change.url

    # Verify that the old password no longer works
    client.get('/logout/')
    resp_old = client.post('/login/', {'username': unique_user, 'password': 'StrongPassword123!'})
    assert resp_old.status_code == 200, "Old password should not work after change"

    # Verify that the new password works
    resp_new = client.post('/login/', {'username': unique_user, 'password': new_password})
    assert resp_new.status_code == 302, "New password failed to log in"
    print("  [OK] Password changed successfully, old password invalidated, new password logs in.")

    # ─────────────────────────────────────────────────────────────
    # 7. BOOKING TICKETS WORKFLOW (TASK 1-5 INTEGRATED)
    # ─────────────────────────────────────────────────────────────
    print("\n[7] Testing Complete Booking Tickets Workflow...")
    # Find an active movie and theater
    theater = Theater.objects.filter(seats__isnull=False).first()
    assert theater is not None, "No active theater with seats found"
    seats = list(Seat.objects.filter(theater=theater, is_booked=False)[:2])
    assert len(seats) >= 1, "No available seats in theater"

    # Sub-test 7a: View Seat Selection Page
    resp_seats = client.get(f'/movies/theater/{theater.id}/seats/book/')
    assert resp_seats.status_code == 200
    seat_content = resp_seats.content.decode('utf-8')
    assert "SMART SEAT RESERVATION" in seat_content
    assert "Hold &amp; Proceed to Payment" in seat_content or "Proceed to Payment" in seat_content

    # Sub-test 7b: Live Status Endpoint
    resp_live = client.get(f'/movies/theater/{theater.id}/seats/live/')
    assert resp_live.status_code == 200
    live_json = resp_live.json()
    assert 'seats' in live_json
    print("  [OK] Sub-test 7a/b: Seat map and live availability feed active.")

    # Sub-test 7c: Reserve Seat (2-minute temporary hold)
    chosen_seat = seats[0]
    resp_book = client.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [str(chosen_seat.id)]})
    assert resp_book.status_code == 302
    assert '/payment/checkout/' in resp_book.url
    order_id = resp_book.url.strip('/').split('/')[-1]

    chosen_seat.refresh_from_db()
    assert chosen_seat.reserved_by == created_user
    assert chosen_seat.reserved_until is not None
    print("  [OK] Sub-test 7c: 2-minute temporary hold established on seat.")

    # Sub-test 7d: Checkout Screen Rendering with 2-min timer & modify button
    resp_checkout = client.get(resp_book.url)
    assert resp_checkout.status_code == 200
    checkout_html = resp_checkout.content.decode('utf-8')
    assert "2-MIN SEAT HOLD TIMER" in checkout_html
    assert "Modify Seats" in checkout_html
    assert "Pay ₹" in checkout_html
    print("  [OK] Sub-test 7d: Checkout screen displays 2-min timer, price breakdown, and Modify Seats action.")

    # Sub-test 7e: Modify Seats Flow
    resp_mod = client.get(f'/movies/payment/modify/{order_id}/')
    assert resp_mod.status_code == 302
    assert f'/movies/theater/{theater.id}/seats/book/' in resp_mod.url
    chosen_seat.refresh_from_db()
    assert chosen_seat.reserved_by is None, "Seat was not released on modify"
    print("  [OK] Sub-test 7e: Modify seats immediately released the held seat.")

    # Sub-test 7f: Re-reserve and complete payment
    resp_rebook = client.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [str(chosen_seat.id)]})
    assert resp_rebook.status_code == 302
    new_order_id = resp_rebook.url.strip('/').split('/')[-1]

    # Simulate payment success with valid signature
    mock_pay_id = f"pay_e2e_{uuid.uuid4().hex[:10]}"
    valid_sig = generate_mock_signature(new_order_id, mock_pay_id)

    resp_verify = client.post('/movies/payment/verify/', {
        'razorpay_order_id': new_order_id,
        'razorpay_payment_id': mock_pay_id,
        'razorpay_signature': valid_sig,
        'payment_method': 'Online / Simulation',
    })
    assert resp_verify.status_code == 302
    assert '/confirmation/' in resp_verify.url

    # Sub-test 7g: Booking Confirmation Page
    resp_conf = client.get(resp_verify.url)
    assert resp_conf.status_code == 200
    conf_html = resp_conf.content.decode('utf-8')
    assert "Booking Confirmed" in conf_html or "Ticket" in conf_html
    assert chosen_seat.seat_number in conf_html
    print("  [OK] Sub-test 7f/g: Payment verified, booking confirmed, confirmation page rendered.")

    # Sub-test 7h: Download PDF Ticket
    booking = Booking.objects.filter(payment__order_id=new_order_id).first()
    assert booking is not None
    resp_dl = client.get(f'/movies/booking/{booking.booking_id}/download-ticket/')
    assert resp_dl.status_code in [200, 302]
    if resp_dl.status_code == 200:
        assert resp_dl.get('Content-Type') == 'application/pdf'
    print("  [OK] Sub-test 7h: PDF ticket download endpoint operational.")

    # Sub-test 7i: Profile Ledger reflects the confirmed booking & payment
    resp_prof2 = client.get('/profile/')
    assert resp_prof2.status_code == 200
    prof2_html = resp_prof2.content.decode('utf-8')
    assert new_order_id in prof2_html or chosen_seat.seat_number in prof2_html
    print("  [OK] Sub-test 7i: Profile booking history & transaction ledger updated.")

    # ─────────────────────────────────────────────────────────────
    # 8. DJANGO ADMIN PANEL ACCESS
    # ─────────────────────────────────────────────────────────────
    print("\n[8] Testing Admin Panel Access...")
    admin_client = Client()
    admin_client.login(username='admin', password='admin123')
    resp_admin = admin_client.get('/admin/')
    assert resp_admin.status_code == 200
    assert "Site administration" in resp_admin.content.decode('utf-8')

    resp_movies_admin = admin_client.get('/admin/movies/movie/')
    assert resp_movies_admin.status_code == 200

    resp_bookings_admin = admin_client.get('/admin/movies/booking/')
    assert resp_bookings_admin.status_code == 200
    print("  [OK] Django admin panel accessible, movie and booking models manage-able.")

    print("\n" + "=" * 70)
    print("ALL E2E CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == '__main__':
    run_comprehensive_e2e_test()
