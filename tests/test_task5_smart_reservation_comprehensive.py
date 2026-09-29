import os, sys, django, time, threading
from datetime import timedelta
sys.path.insert(0, r'd:\Intership project\django-bookmyshow-clone')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.utils import timezone
from movies.models import Movie, Theater, Seat, PaymentTransaction, Booking
from movies.payment_service import (
    release_expired_reservations,
    process_successful_payment,
    process_failed_payment,
    generate_mock_signature
)

print("=" * 70)
print("TASK 5: SMART SEAT RESERVATION & LIVE AVAILABILITY TEST SUITE")
print("=" * 70)

# Setup test users
alice, _ = User.objects.get_or_create(username='alice', defaults={'email': 'alice@example.com'})
alice.set_password('testpass123')
alice.save()

bob, _ = User.objects.get_or_create(username='bob', defaults={'email': 'bob@example.com'})
bob.set_password('testpass123')
bob.save()

# Setup test movie and theater with 6 seats
movie = Movie.objects.first()
theater, _ = Theater.objects.get_or_create(
    name='IMAX Arena Test',
    city='Hyderabad',
    movie=movie,
    defaults={'time': timezone.now() + timedelta(days=1), 'ticket_price': 250.00}
)

# Clear any pre-existing seats for this test theater
Seat.objects.filter(theater=theater).delete()
seats = [
    Seat.objects.create(theater=theater, seat_number=f'T{i}', is_booked=False)
    for i in range(1, 7)
]
s1, s2, s3, s4, s5, s6 = seats

client_alice = Client()
client_alice.post('/login/', {'username': 'alice', 'password': 'testpass123'})

client_bob = Client()
client_bob.post('/login/', {'username': 'bob', 'password': 'testpass123'})

print("\n--- TEST 1: Live Seat Status API & Initial Availability ---")
live_resp = client_alice.get(f'/movies/theater/{theater.id}/seats/live/')
assert live_resp.status_code == 200
data = live_resp.json()
assert data['total_seats'] == 6
assert data['available_count'] == 6
assert data['reserved_count'] == 0
assert data['booked_count'] == 0
print(f"[PASS] Initial live feed correct: 6 available, 0 reserved, 0 booked")

print("\n--- TEST 2: Multi-Seat Selection & 2-Minute Temporary Hold ---")
# Alice reserves s1 and s2
post_resp = client_alice.post(f'/movies/theater/{theater.id}/seats/book/', {
    'seats': [s1.id, s2.id]
}, follow=False)

assert post_resp.status_code == 302, f"Expected 302 redirect, got {post_resp.status_code}"
checkout_url = post_resp.get('Location')
assert '/movies/payment/' in checkout_url
order_id = checkout_url.strip('/').split('/')[-1]
print(f"[PASS] Alice selected T1 & T2, redirected to checkout: {checkout_url}")

# Verify database state
s1.refresh_from_db()
s2.refresh_from_db()
now = timezone.now()
assert s1.reserved_by == alice
assert s2.reserved_by == alice
assert s1.reserved_until > now
assert s2.reserved_until > now
hold_duration = (s1.reserved_until - now).total_seconds()
assert 110 <= hold_duration <= 125, f"Hold duration unexpected: {hold_duration}s"
print(f"[PASS] Seats T1 & T2 locked with {hold_duration:.1f}s hold window (2 minutes)")

# Verify Live Status for Alice vs Bob
live_alice = client_alice.get(f'/movies/theater/{theater.id}/seats/live/').json()
alice_s1 = next(s for s in live_alice['seats'] if s['id'] == s1.id)
assert alice_s1['status'] == 'selected_by_me', f"Expected 'selected_by_me', got {alice_s1['status']}"

live_bob = client_bob.get(f'/movies/theater/{theater.id}/seats/live/').json()
bob_s1 = next(s for s in live_bob['seats'] if s['id'] == s1.id)
assert bob_s1['status'] == 'reserved', f"Expected 'reserved', got {bob_s1['status']}"
assert bob_s1['seconds_left'] > 0
print(f"[PASS] Status indicators verified: Alice sees 'selected_by_me', Bob sees 'reserved'")

print("\n--- TEST 3: Collision Rejection (Bob cannot reserve Alice's held seats) ---")
# Bob attempts to reserve s1 (held by Alice) and s3 (available)
bob_post = client_bob.post(f'/movies/theater/{theater.id}/seats/book/', {
    'seats': [s1.id, s3.id]
}, follow=True)

# Bob should be denied, kept on seat selection page with warning
assert bob_post.status_code == 200
bob_html = bob_post.content.decode('utf-8')
assert "Some selected seats were just reserved or booked by another patron" in bob_html
s3.refresh_from_db()
assert s3.reserved_by is None, "s3 should not be locked when collision occurs"
print(f"[PASS] Bob's attempt to take Alice's seat was cleanly blocked with clear error alert")

print("\n--- TEST 4: Modify Seat Selection Flow ---")
# Alice clicks 'Modify Seats' before paying
modify_resp = client_alice.get(f'/movies/payment/modify/{order_id}/', follow=False)
assert modify_resp.status_code == 302
assert f'/movies/theater/{theater.id}/seats/book/' in modify_resp.get('Location')

s1.refresh_from_db()
s2.refresh_from_db()
assert s1.reserved_by is None, "s1 should be released on modify"
assert s1.reserved_until is None, "s1 reserved_until cleared"
assert s2.reserved_by is None, "s2 should be released on modify"

# Verify live feed after modify
live_after_modify = client_bob.get(f'/movies/theater/{theater.id}/seats/live/').json()
assert live_after_modify['available_count'] == 6
print(f"[PASS] Modify seats immediately released T1 & T2 back to available pool")

print("\n--- TEST 5: Automatic Release After 2-Minute Expiry ---")
# Alice reserves s4 and s5
post_resp2 = client_alice.post(f'/movies/theater/{theater.id}/seats/book/', {
    'seats': [s4.id, s5.id]
}, follow=False)
order_id2 = post_resp2.get('Location').strip('/').split('/')[-1]

# Artificially fast-forward time to simulate 2 minutes passing (expiry)
s4.reserved_until = timezone.now() - timedelta(seconds=5)
s4.save(update_fields=['reserved_until'])
s5.reserved_until = timezone.now() - timedelta(seconds=5)
s5.save(update_fields=['reserved_until'])

# 5a: Expiry on live feed poll
released = release_expired_reservations(theater=theater)
assert released == 2, f"Expected 2 released, got {released}"
s4.refresh_from_db()
assert s4.reserved_by is None
assert s4.reserved_until is None
print(f"[PASS] 5a: Expired 2-minute hold automatically freed by live release monitor")

# 5b: Expiry on checkout load
checkout_expired = client_alice.get(f'/movies/payment/checkout/{order_id2}/', follow=True)
assert checkout_expired.status_code == 200
assert "Your 2-minute seat reservation expired. Please re-select your seats." in checkout_expired.content.decode('utf-8')
print(f"[PASS] 5b: Checkout screen auto-detects expired reservation and redirects with warning")

print("\n--- TEST 6: Concurrency Safety Under Simultaneous Requests ---")
# Both Alice and Bob attempt to book the exact same seat s6 simultaneously via 2 threads
results = {}

def book_seat_simultaneous(client_name, client_obj, seat_id):
    resp = client_obj.post(f'/movies/theater/{theater.id}/seats/book/', {
        'seats': [seat_id]
    }, follow=False)
    results[client_name] = resp.status_code

t1 = threading.Thread(target=book_seat_simultaneous, args=('alice', client_alice, s6.id))
t2 = threading.Thread(target=book_seat_simultaneous, args=('bob', client_bob, s6.id))

t1.start()
t2.start()
t1.join()
t2.join()

print(f"   Concurrent results: Alice={results.get('alice')}, Bob={results.get('bob')}")
# Exactly one should get 302 (success redirect to checkout), other gets 200 (stay on seat page with collision error)
status_codes = [results['alice'], results['bob']]
assert 302 in status_codes, "At least one client must succeed"
assert 200 in status_codes, "Exactly one client must be blocked from double reservation"
print(f"[PASS] Concurrency lock safely prevented double reservation: 1 succeeded (302), 1 rejected (200)")

print("\n--- TEST 7: Payment Confirmation Converts Reservation to Permanent Booking ---")
# The winning reservation is finalized
winning_user = alice if results['alice'] == 302 else bob
winning_txn = PaymentTransaction.objects.filter(user=winning_user, theater=theater, status=PaymentTransaction.STATUS_PENDING).first()
assert winning_txn is not None

# Confirm payment
bookings = process_successful_payment(winning_txn.order_id, payment_id='pay_test_task5_final')
assert len(bookings) == 1
assert bookings[0].seat == s6

s6.refresh_from_db()
assert s6.is_booked is True, "Seat must now be permanently is_booked=True"
assert s6.reserved_by is None
assert s6.reserved_until is None

# Duplicate confirmation idempotency check
dup_bookings = process_successful_payment(winning_txn.order_id, payment_id='pay_test_task5_final')
assert len(dup_bookings) == 1
assert Booking.objects.filter(seat=s6).count() == 1, "Duplicate bookings must NEVER be created"
print(f"[PASS] Confirmed payment finalized booking with 0 hold remnants and strict idempotency")

# Cleanup test fixtures
Booking.objects.filter(theater=theater).delete()
PaymentTransaction.objects.filter(theater=theater).delete()
Seat.objects.filter(theater=theater).delete()
theater.delete()
alice.delete()
bob.delete()

print("\n" + "=" * 70)
print("ALL 7 TASK 5 REQUIREMENTS FULLY VERIFIED & PASSING 100%!")
print("=" * 70)
