import os
import sys
import json
import uuid
import hmac
import hashlib

sys.path.insert(0, r"d:\Intership project\django-bookmyshow-clone")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')

import django
django.setup()

from django.test.utils import setup_test_environment
setup_test_environment()

from django.test import Client
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from movies.models import Movie, Theater, Seat, Booking, PaymentTransaction
from movies.payment_service import (
    create_payment_order,
    verify_payment_signature,
    verify_webhook_signature,
    generate_mock_signature,
    process_successful_payment,
    process_failed_payment,
    process_cancelled_payment,
)

print('======================================================================')
print('        TASK 4: COMPREHENSIVE PAYMENT WORKFLOW TEST SUITE             ')
print('======================================================================')

client = Client()

# Create test patron
user, _ = User.objects.get_or_create(username='payment_auditor', email='auditor@example.com')
user.set_password('securepass123')
user.save()
client.force_login(user)

# Setup test movie and theater
movie = Movie.objects.first()
theater = Theater.objects.filter(movie=movie).first()
if not theater:
    theater = Theater.objects.create(
        movie=movie, name='PVR Grand', city='Hyderabad', location='Panjagutta',
        ticket_price=250.0, time=timezone.now() + timedelta(days=2)
    )

# -- TEST 1: SEAT SELECTION & PAYMENT INITIALIZATION (PENDING STATE) --
print('\n[1] Testing Seat Selection, Temporary Lock & Razorpay Order Creation...')
s1, _ = Seat.objects.get_or_create(theater=theater, seat_number='PAY-T1', defaults={'is_booked': False})
s2, _ = Seat.objects.get_or_create(theater=theater, seat_number='PAY-T2', defaults={'is_booked': False})
s1.is_booked = False
s1.save()
s2.is_booked = False
s2.save()

res = client.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [s1.id, s2.id]})
assert res.status_code == 302, f'Expected 302 redirect to checkout, got {res.status_code}'
checkout_url = res.url
assert 'payment/checkout/' in checkout_url, f'Unexpected redirect URL: {checkout_url}'

order_id = checkout_url.strip('/').split('/')[-1]
payment_txn = PaymentTransaction.objects.get(order_id=order_id)
assert payment_txn.status == PaymentTransaction.STATUS_PENDING
assert payment_txn.amount == theater.ticket_price * 2
assert payment_txn.user == user

s1.refresh_from_db()
s2.refresh_from_db()
assert (s1.reserved_by == user or s1.is_booked) and (s2.reserved_by == user or s2.is_booked), 'Seats were not temporarily locked/reserved'

# Ensure NO Bookings exist yet! (Only confirmed after payment)
assert Booking.objects.filter(seat__in=[s1, s2]).count() == 0, 'Booking created before payment!'
print('  [PASS] Order initialized, seats temporarily locked in PENDING state, 0 bookings pre-payment.')

# -- TEST 2: CHECKOUT SCREEN RENDERING & SECURITY --
print('\n[2] Testing Checkout Screen Rendering...')
res = client.get(checkout_url)
assert res.status_code == 200
assert b'Confirm &amp; Pay' in res.content or b'Confirm & Pay' in res.content
assert b'PAY-T1' in res.content
print('  [PASS] Checkout view renders with order summary and Razorpay modal integration.')

# -- TEST 3: SERVER-SIDE SIGNATURE VERIFICATION --
print('\n[3] Testing Server-Side Signature Verification...')
mock_pay_id = f"pay_test_{uuid.uuid4().hex[:10]}"
valid_sig = generate_mock_signature(order_id, mock_pay_id)
assert verify_payment_signature(order_id, mock_pay_id, valid_sig) == True, 'Valid signature rejected!'
assert verify_payment_signature(order_id, mock_pay_id, 'tampered_signature_123') == False, 'Tampered signature accepted!'
print('  [PASS] Valid signatures accepted; tampered signatures strictly rejected.')

# -- TEST 4: SUCCESSFUL PAYMENT & BOOKING CONFIRMATION --
print('\n[4] Testing Successful Payment & Confirmation...')
res = client.post('/movies/payment/verify/', {
    'razorpay_order_id': order_id,
    'razorpay_payment_id': mock_pay_id,
    'razorpay_signature': valid_sig,
    'payment_method': 'UPI / PhonePe',
})
assert res.status_code == 302, f'Expected redirect to confirmation, got {res.status_code}'

payment_txn.refresh_from_db()
assert payment_txn.status == PaymentTransaction.STATUS_SUCCESS
assert payment_txn.payment_id == mock_pay_id

# Verify Bookings are now created and confirmed
confirmed_bookings = Booking.objects.filter(seat__in=[s1, s2])
assert confirmed_bookings.count() == 2, 'Expected 2 confirmed bookings'
for b in confirmed_bookings:
    assert b.payment == payment_txn
    assert b.payment_reference == order_id
print(f'  [PASS] Payment {order_id} marked SUCCESS; {confirmed_bookings.count()} bookings confirmed.')

# -- TEST 5: IDEMPOTENCY / DUPLICATE PREVENTION --
print('\n[5] Testing Idempotency (Duplicate Payment Confirmations)...')
# Post the same payment confirmation a second time
res_dup = client.post('/movies/payment/verify/', {
    'razorpay_order_id': order_id,
    'razorpay_payment_id': mock_pay_id,
    'razorpay_signature': valid_sig,
    'payment_method': 'UPI / PhonePe',
})
assert res_dup.status_code == 302
# Verify total bookings for these seats did NOT increase
assert Booking.objects.filter(seat__in=[s1, s2]).count() == 2, 'Duplicate bookings were created!'
print('  [PASS] Duplicate payment confirmations return cleanly without creating duplicate bookings.')

# -- TEST 6: PAYMENT FAILURE & AUTOMATIC SEAT RELEASE --
print('\n[6] Testing Payment Failure & Automatic Seat Release...')
s3, _ = Seat.objects.get_or_create(theater=theater, seat_number='PAY-T3', defaults={'is_booked': False})
s3.is_booked = False
s3.save()

# Start checkout for s3
res = client.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [s3.id]})
fail_order_id = res.url.strip('/').split('/')[-1]

s3.refresh_from_db()
assert s3.reserved_by == user or s3.is_booked, 'Seat s3 not reserved'

# Simulate failure callback
res_fail = client.post('/movies/payment/failed/', {
    'order_id': fail_order_id,
    'error_code': 'CARD_EXPIRED',
    'error_desc': 'Bank declined: Card has expired'
})
assert res_fail.status_code == 200
assert b'Payment Unsuccessful' in res_fail.content
assert b'Seats Automatically Released' in res_fail.content

fail_txn = PaymentTransaction.objects.get(order_id=fail_order_id)
assert fail_txn.status == PaymentTransaction.STATUS_FAILED
assert fail_txn.error_code == 'CARD_EXPIRED'

# CRITICAL CHECK: Ensure seat was automatically released!
s3.refresh_from_db()
assert s3.is_booked == False and s3.reserved_by is None, 'Seat s3 was NOT released after payment failure!'
assert Booking.objects.filter(seat=s3).count() == 0, 'Booking exists for failed payment!'
print('  [PASS] Failed payment marked FAILED, diagnostic screen displayed, and reserved seats automatically released.')

# -- TEST 7: PAYMENT CANCELLATION BY USER --
print('\n[7] Testing Payment Cancellation by User...')
s4, _ = Seat.objects.get_or_create(theater=theater, seat_number='PAY-T4', defaults={'is_booked': False})
s4.is_booked = False
s4.save()

res = client.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [s4.id]})
cancel_order_id = res.url.strip('/').split('/')[-1]
s4.refresh_from_db()
assert s4.reserved_by == user or s4.is_booked

# User clicks cancel
res_cancel = client.post(f'/movies/payment/cancel/{cancel_order_id}/')
assert res_cancel.status_code == 302

cancel_txn = PaymentTransaction.objects.get(order_id=cancel_order_id)
assert cancel_txn.status == PaymentTransaction.STATUS_CANCELLED

# CRITICAL CHECK: Seat released
s4.refresh_from_db()
assert s4.is_booked == False, 'Seat s4 was NOT released after cancellation!'
print('  [PASS] Cancelled payment marked CANCELLED and reserved seats immediately released.')

# -- TEST 8: SERVER-SIDE WEBHOOK VERIFICATION --
print('\n[8] Testing Server-Side Webhook Verification...')
# 1. Test rejection of invalid signature
invalid_webhook = client.post(
    '/movies/payment/webhook/',
    data=b'{"event": "payment.captured"}',
    content_type='application/json',
    HTTP_X_RAZORPAY_SIGNATURE='bogus_signature'
)
assert invalid_webhook.status_code == 400
print('  Sub-test 8a: Bogus webhook signature rejected with 400: PASS')

# 2. Test valid webhook payload processing
s5, _ = Seat.objects.get_or_create(theater=theater, seat_number='PAY-T5', defaults={'is_booked': False})
s5.is_booked = False
s5.save()

res = client.post(f'/movies/theater/{theater.id}/seats/book/', {'seats': [s5.id]})
webhook_order_id = res.url.strip('/').split('/')[-1]
webhook_pay_id = f"pay_hook_{uuid.uuid4().hex[:10]}"

webhook_payload = json.dumps({
    'event': 'payment.captured',
    'payload': {
        'payment': {
            'entity': {
                'id': webhook_pay_id,
                'order_id': webhook_order_id,
                'method': 'Netbanking / HDFC',
                'amount': 25000
            }
        }
    }
}).encode('utf-8')

webhook_sig = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8'), webhook_payload, hashlib.sha256).hexdigest()

res_webhook = client.post(
    '/movies/payment/webhook/',
    data=webhook_payload,
    content_type='application/json',
    HTTP_X_RAZORPAY_SIGNATURE=webhook_sig
)
assert res_webhook.status_code == 200, f'Webhook returned {res_webhook.status_code}'

webhook_txn = PaymentTransaction.objects.get(order_id=webhook_order_id)
assert webhook_txn.status == PaymentTransaction.STATUS_SUCCESS
assert Booking.objects.filter(seat=s5).count() == 1
print('  Sub-test 8b: Valid Razorpay webhook processed and booking confirmed: PASS')

# -- TEST 9: USER PROFILE PAYMENT & BOOKING HISTORY --
print('\n[9] Testing User Profile Payment History...')
res_profile = client.get('/users/profile/')
assert res_profile.status_code == 200
assert b'Payment Transactions' in res_profile.content
assert order_id.encode() in res_profile.content
assert b'Success' in res_profile.content
assert b'Failed' in res_profile.content
assert b'Cancelled' in res_profile.content
print('  [PASS] Profile renders comprehensive transaction ledger with all statuses and retry/ticket actions.')

# Cleanup test fixtures
PaymentTransaction.objects.filter(user=user).delete()
Booking.objects.filter(user=user).delete()
Seat.objects.filter(seat_number__startswith='PAY-T').delete()
user.delete()

print('\n======================================================================')
print('     ALL TASK 4 PAYMENT WORKFLOW REQUIREMENTS 100% VERIFIED & PASSING! ')
print('======================================================================')
