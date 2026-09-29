import os
import sys
import django
from datetime import timedelta
import threading
import queue

# Setup Django environment
sys.path.append(os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction, connection
from movies.models import Movie, Theater, Seat, PaymentTransaction, Booking
from movies.payment_service import (
    process_successful_payment,
    process_failed_payment,
    process_cancelled_payment,
    release_expired_reservations,
    generate_mock_signature
)


def run_tests():
    print("=" * 60)
    print("RUNNING TASK 5 SMART SEAT RESERVATION TEST SUITE")
    print("=" * 60)

    # 1. Setup Test Users and Theater
    user1, _ = User.objects.get_or_create(username='alice', defaults={'email': 'alice@example.com'})
    user1.set_password('pass1234')
    user1.save()

    user2, _ = User.objects.get_or_create(username='bob', defaults={'email': 'bob@example.com'})
    user2.set_password('pass1234')
    user2.save()

    movie = Movie.objects.first()
    if not movie:
        movie = Movie.objects.create(name='Inception', rating=8.8, popularity=95.0)

    theater = Theater.objects.filter(movie=movie).first()
    if not theater:
        theater = Theater.objects.create(movie=movie, name='PVR Icon', city='Mumbai', ticket_price=250.0)

    # Clean up seats for this theater
    Seat.objects.filter(theater=theater).delete()
    s1 = Seat.objects.create(theater=theater, seat_number='T1')
    s2 = Seat.objects.create(theater=theater, seat_number='T2')
    s3 = Seat.objects.create(theater=theater, seat_number='T3')

    client1 = Client()
    client1.login(username='alice', password='pass1234')

    client2 = Client()
    client2.login(username='bob', password='pass1234')

    # -------------------------------------------------------------
    # Test 1: Live Seat Status API
    # -------------------------------------------------------------
    print("\n[Test 1] Testing Live Seat Status API...")
    resp = client1.get(f'/movies/theater/{theater.id}/seats/live/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert 'seats' in data and data['total_seats'] == 3
    assert data['available_count'] == 3
    assert data['reserved_count'] == 0
    assert data['booked_count'] == 0
    for s in data['seats']:
        assert s['status'] == 'available'
    print("  PASS: Live Seat Status API returned correct 3 available seats.")

    # -------------------------------------------------------------
    # Test 2: 2-Minute Temporary Reservation & Multi-Seat Selection
    # -------------------------------------------------------------
    print("\n[Test 2] Testing 2-Minute Temporary Hold on Seat Selection...")
    resp = client1.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [str(s1.id), str(s2.id)]})
    assert resp.status_code == 302, f"Expected redirect, got {resp.status_code}"
    redirect_url = resp.url
    assert '/payment/checkout/' in redirect_url
    order_id = redirect_url.split('/payment/checkout/')[1].strip('/')

    s1.refresh_from_db()
    s2.refresh_from_db()
    assert s1.reserved_by == user1, "Seat 1 not reserved by user1"
    assert s2.reserved_by == user1, "Seat 2 not reserved by user1"
    assert s1.is_booked is False, "Seat 1 should not be marked booked yet"
    assert s2.is_booked is False, "Seat 2 should not be marked booked yet"
    assert s1.reserved_until is not None
    now = timezone.now()
    diff = (s1.reserved_until - now).total_seconds()
    assert 100 <= diff <= 125, f"Reservation duration {diff}s not in expected 2-minute window (~120s)"
    print(f"  PASS: Seats s1 and s2 reserved for Alice with ~{int(diff)}s hold window.")

    # Check status from Bob's perspective
    resp_bob = client2.get(f'/movies/theater/{theater.id}/seats/live/')
    bob_data = resp_bob.json()
    bob_seats_map = {s['seat_number']: s for s in bob_data['seats']}
    assert bob_seats_map['T1']['status'] == 'reserved', f"Expected reserved, got {bob_seats_map['T1']['status']}"
    assert bob_seats_map['T2']['status'] == 'reserved', f"Expected reserved, got {bob_seats_map['T2']['status']}"
    assert bob_seats_map['T3']['status'] == 'available'
    assert bob_data['reserved_count'] == 2
    assert bob_data['available_count'] == 1
    print("  PASS: Bob sees T1 and T2 as 'reserved' by another patron.")

    # Check status from Alice's perspective
    resp_alice = client1.get(f'/movies/theater/{theater.id}/seats/live/')
    alice_data = resp_alice.json()
    alice_seats_map = {s['seat_number']: s for s in alice_data['seats']}
    assert alice_seats_map['T1']['status'] == 'selected_by_me'
    assert alice_seats_map['T2']['status'] == 'selected_by_me'
    print("  PASS: Alice sees T1 and T2 as 'selected_by_me'.")

    # -------------------------------------------------------------
    # Test 3: Preventing Other Users from Stealing Reserved Seats
    # -------------------------------------------------------------
    print("\n[Test 3] Testing Collision Rejection for Another User...")
    resp_bob_book = client2.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [str(s1.id)]})
    assert resp_bob_book.status_code == 200, "Expected re-render of seat page with error"
    assert "reserved or booked by another patron" in resp_bob_book.content.decode('utf-8')
    s1.refresh_from_db()
    assert s1.reserved_by == user1, "Seat 1 reservation should still belong to Alice"
    print("  PASS: Bob was blocked from booking Alice's temporarily reserved seat.")

    # -------------------------------------------------------------
    # Test 4: Modifying Seat Selection Before Payment
    # -------------------------------------------------------------
    print("\n[Test 4] Testing 'Modify Seat Selection' Flow...")
    modify_resp = client1.get(f'/movies/payment/modify/{order_id}/')
    assert modify_resp.status_code == 302
    assert f'/movies/theater/{theater.id}/seats/book/' in modify_resp.url

    s1.refresh_from_db()
    s2.refresh_from_db()
    assert s1.reserved_by is None, "Seat 1 was not released on modify"
    assert s1.reserved_until is None, "Seat 1 reserved_until not cleared"
    assert s2.reserved_by is None, "Seat 2 was not released on modify"

    p_txn = PaymentTransaction.objects.get(order_id=order_id)
    assert p_txn.status == PaymentTransaction.STATUS_CANCELLED
    print("  PASS: Modify seats released s1 and s2 immediately; cancelled old order.")

    # -------------------------------------------------------------
    # Test 5: Automatic Release When 2 Minutes Expire
    # -------------------------------------------------------------
    print("\n[Test 5] Testing Automatic Expiry of 2-Minute Hold...")
    # Alice reserves T3
    resp_t3 = client1.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [str(s3.id)]})
    assert resp_t3.status_code == 302
    order_id_t3 = resp_t3.url.split('/payment/checkout/')[1].strip('/')

    s3.refresh_from_db()
    assert s3.reserved_by == user1

    # Simulate expiration by moving reserved_until 1 second into the past
    s3.reserved_until = timezone.now() - timedelta(seconds=1)
    s3.save(update_fields=['reserved_until'])

    # Calling live seat status should trigger auto-release
    resp_expire = client2.get(f'/movies/theater/{theater.id}/seats/live/')
    s3.refresh_from_db()
    assert s3.reserved_by is None, "Seat 3 was not released after 2 minutes expired"
    assert s3.reserved_until is None, "Seat 3 reserved_until not cleared"
    print("  PASS: Expired reservation automatically released on live feed.")

    # Checking out on expired reservation should redirect with warning
    resp_checkout_exp = client1.get(f'/movies/payment/checkout/{order_id_t3}/')
    assert resp_checkout_exp.status_code == 302, "Expected redirect on expired checkout"
    assert f'/movies/theater/{theater.id}/seats/book/' in resp_checkout_exp.url
    print("  PASS: Visiting checkout with expired reservation automatically releases seats and redirects.")

    # -------------------------------------------------------------
    # Test 6: Concurrency Safety Under Simultaneous Requests
    # -------------------------------------------------------------
    print("\n[Test 6] Testing Concurrency Safety with Simultaneous Threads...")
    # Reset seat T1 to available
    s1.is_booked = False
    s1.reserved_by = None
    s1.reserved_until = None
    s1.save()

    results = queue.Queue()

    def attempt_booking(user_obj, seat_id):
        c = Client()
        c.force_login(user_obj)
        try:
            r = c.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [str(seat_id)]})
            results.put((user_obj.username, r.status_code, r.url if r.status_code == 302 else 'Failed'))
        except Exception as e:
            results.put((user_obj.username, 500, str(e)))
        finally:
            connection.close()

    # Launch two simultaneous booking attempts on seat T1
    t_alice = threading.Thread(target=attempt_booking, args=(user1, s1.id))
    t_bob = threading.Thread(target=attempt_booking, args=(user2, s1.id))

    t_alice.start()
    t_bob.start()

    t_alice.join()
    t_bob.join()

    outcomes = []
    while not results.empty():
        outcomes.append(results.get())

    success_count = sum(1 for o in outcomes if o[1] == 302)
    fail_count = sum(1 for o in outcomes if o[1] == 200)
    print(f"  Outcomes: {outcomes}")
    assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
    assert fail_count == 1, f"Expected exactly 1 failure, got {fail_count}"

    s1.refresh_from_db()
    assert s1.reserved_by is not None, "Seat 1 must be reserved"
    print(f"  PASS: Exactly 1 concurrent reservation succeeded (reserved by {s1.reserved_by.username}), second request cleanly blocked!")

    # -------------------------------------------------------------
    # Test 7: Successful Payment Finalization
    # -------------------------------------------------------------
    print("\n[Test 7] Testing Payment Confirmation Updates...")
    import uuid
    test_final_order_id = f"order_task5_{uuid.uuid4().hex[:10]}"
    # Clean up and reserve s1 fresh for Alice
    s1.is_booked = False
    s1.reserved_by = user1
    s1.reserved_until = timezone.now() + timedelta(seconds=120)
    s1.save()

    txn = PaymentTransaction.objects.create(
        order_id=test_final_order_id,
        user=user1,
        movie=movie,
        theater=theater,
        amount=250.0,
        currency='INR',
        status=PaymentTransaction.STATUS_PENDING
    )
    txn.seats.set([s1])

    bookings = process_successful_payment(test_final_order_id, f"pay_{uuid.uuid4().hex[:10]}")
    assert len(bookings) == 1
    s1.refresh_from_db()
    assert s1.is_booked is True, "Seat 1 not marked booked after successful payment"
    assert s1.reserved_by is None, "Seat 1 reserved_by not cleared"
    assert s1.reserved_until is None, "Seat 1 reserved_until not cleared"
    txn.refresh_from_db()
    assert txn.status == PaymentTransaction.STATUS_SUCCESS
    print("  PASS: Confirmed payment marked seat booked and cleared temporary hold.")

    print("\n" + "=" * 60)
    print("ALL TASK 5 TESTS PASSED SUCCESSFULLY! (7/7)")
    print("=" * 60)


if __name__ == '__main__':
    run_tests()
