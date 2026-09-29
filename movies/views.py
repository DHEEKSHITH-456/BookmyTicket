import os
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q, Min, Max, Count, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, Http404, JsonResponse
from django.conf import settings
from django.utils import timezone
from .models import Movie, Theater, Seat, Booking, Review, PaymentTransaction
from .payment_service import (
    create_payment_order,
    verify_payment_signature,
    verify_webhook_signature,
    process_successful_payment,
    process_failed_payment,
    process_cancelled_payment,
    release_expired_reservations,
    generate_mock_signature,
)
import uuid


# ════════════════════════════════════════════════
#  TASK 1: Recommendation Engine
# ════════════════════════════════════════════════

def get_recommended_movies(request, current_movie_id=None):
    """
    Intelligent recommendation engine based on:
    1. User's past booking history (favorite genres and languages)
    2. User's recently viewed movies stored in session
    3. Fallback to top-rated & most popular movies with active showtimes
    """
    def _attach_primary_theaters(movie_list):
        for m in movie_list:
            m.primary_theater = m.theaters.order_by('time').first()
        return movie_list

    # 1. Recommendation from Booking History (if authenticated)
    if request.user.is_authenticated:
        user_bookings = Booking.objects.filter(user=request.user).select_related('movie')
        if user_bookings.exists():
            booked_movie_ids = list(user_bookings.values_list('movie_id', flat=True))

            favorite_genres = set()
            favorite_languages = set()
            for b in user_bookings:
                if b.movie:
                    for g in b.movie.genres.all():
                        favorite_genres.add(g.name)
                    for l in b.movie.languages.all():
                        favorite_languages.add(l.name)

            genre_query = Q()
            for g in favorite_genres:
                genre_query |= Q(genres__name__icontains=g)

            rec_qs = Movie.objects.filter(theaters__isnull=False).exclude(id__in=booked_movie_ids)
            if current_movie_id:
                rec_qs = rec_qs.exclude(id=current_movie_id)

            history_recs = list(rec_qs.filter(
                genre_query | Q(languages__name__in=favorite_languages)
            ).distinct().order_by('-rating', '-popularity')[:6])
            if history_recs:
                for m in history_recs:
                    m.rec_badge = "Based on your booking history"
                return _attach_primary_theaters(history_recs)

    # 2. Recommendation from Recently Viewed (session-based)
    recently_viewed_ids = request.session.get('recently_viewed', [])
    if recently_viewed_ids:
        viewed_movies = Movie.objects.filter(id__in=recently_viewed_ids)
        viewed_genres = set()
        for vm in viewed_movies:
            for g in vm.genres.all():
                viewed_genres.add(g.name)

        genre_q = Q()
        for g in viewed_genres:
            genre_q |= Q(genres__name__icontains=g)

        rec_qs = Movie.objects.filter(theaters__isnull=False).exclude(id__in=recently_viewed_ids)
        if current_movie_id:
            rec_qs = rec_qs.exclude(id=current_movie_id)

        view_recs = list(rec_qs.filter(genre_q).distinct().order_by('-rating', '-popularity')[:6])
        if view_recs:
            for m in view_recs:
                m.rec_badge = "Because you recently viewed similar movies"
            return _attach_primary_theaters(view_recs)

    # 3. Fallback: Trending & Top Rated Movies with active theaters
    rec_qs = Movie.objects.filter(theaters__isnull=False).distinct()
    if current_movie_id:
        rec_qs = rec_qs.exclude(id=current_movie_id)

    top_recs = list(rec_qs.order_by('-rating', '-popularity')[:6])
    for m in top_recs:
        m.rec_badge = "Trending & Highest Rated"
    return _attach_primary_theaters(top_recs)



# ════════════════════════════════════════════════
#  TASK 1: Movie Discovery with Search & Filters
# ════════════════════════════════════════════════

def movie_list(request):
    """
    Advanced Movie Discovery Module:
    - Search by title, cast, description, genre
    - Filters: Genre, Language, City, Theater, Rating, Release Date, Show Timing, Ticket Price
    - Sorting: Popularity, Newest, Rating, Price (Low to High, High to Low)
    - Dynamic Match Count
    - Dataset Pagination
    - 'Recommended for You' section
    """
    search_query = request.GET.get('search', '').strip()
    selected_genre = request.GET.get('genre', '').strip()
    selected_language = request.GET.get('language', '').strip()
    selected_city = request.GET.get('city', '').strip()
    selected_theater = request.GET.get('theater', '').strip()
    selected_rating = request.GET.get('rating', '').strip()
    selected_timing = request.GET.get('timing', request.GET.get('show_timing', '')).strip()
    selected_release = request.GET.get('release', request.GET.get('status', request.GET.get('release_date', ''))).strip()
    selected_max_price = request.GET.get('max_price', request.GET.get('price', '')).strip()
    sort_by = request.GET.get('sort', 'popularity').strip()

    movies = Movie.objects.annotate(
        min_ticket_price=Min('theaters__ticket_price'),
        max_ticket_price=Max('theaters__ticket_price'),
        theater_count=Count('theaters', distinct=True)
    )

    if search_query:
        movies = movies.filter(
            Q(name__icontains=search_query) |
            Q(cast_members__name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(genres__name__icontains=search_query)
        )
    if selected_genre and selected_genre != 'All':
        movies = movies.filter(genres__name__icontains=selected_genre)
    if selected_language and selected_language != 'All':
        movies = movies.filter(languages__name__iexact=selected_language)
    if selected_city and selected_city != 'All':
        movies = movies.filter(theaters__city__iexact=selected_city)
    if selected_theater and selected_theater != 'All':
        movies = movies.filter(theaters__name__icontains=selected_theater)
    if selected_rating:
        try:
            movies = movies.filter(rating__gte=float(selected_rating))
        except ValueError:
            pass
    if selected_timing and selected_timing != 'All':
        t = selected_timing.lower()
        if t == 'morning':
            movies = movies.filter(theaters__time__hour__gte=6, theaters__time__hour__lt=12)
        elif t == 'afternoon':
            movies = movies.filter(theaters__time__hour__gte=12, theaters__time__hour__lt=17)
        elif t == 'evening':
            movies = movies.filter(theaters__time__hour__gte=17, theaters__time__hour__lt=21)
        elif t == 'night':
            movies = movies.filter(Q(theaters__time__hour__gte=21) | Q(theaters__time__hour__lt=6))

    today = date.today()
    if selected_release == 'now_showing':
        movies = movies.filter(release_date__lte=today)
    elif selected_release == 'upcoming':
        movies = movies.filter(release_date__gt=today)
    elif selected_release and selected_release != 'All':
        movies = movies.filter(release_date__icontains=selected_release)

    if selected_max_price:
        try:
            movies = movies.filter(theaters__ticket_price__lte=float(selected_max_price))
        except ValueError:
            pass

    movies = movies.distinct()

    if sort_by in ['newest', '-release_date']:
        movies = movies.order_by('-release_date', '-id')
    elif sort_by in ['rating', '-rating']:
        movies = movies.order_by('-rating', '-popularity')
    elif sort_by in ['price_asc', 'price', 'ticket_price']:
        movies = movies.order_by('min_ticket_price', '-rating')
    elif sort_by in ['price_desc', '-price', '-ticket_price']:
        movies = movies.order_by('-min_ticket_price', '-rating')
    else:
        movies = movies.order_by('-popularity', '-rating')

    total_matches = movies.count()

    paginator = Paginator(movies, 6)
    page = request.GET.get('page', 1)
    try:
        paginated_movies = paginator.page(page)
    except PageNotAnInteger:
        paginated_movies = paginator.page(1)
    except EmptyPage:
        paginated_movies = paginator.page(paginator.num_pages)

    from .models import Genre, Language
    all_genres = list(Genre.objects.values_list('name', flat=True).order_by('name'))
    all_languages = list(Language.objects.values_list('name', flat=True).order_by('name'))
    all_cities = sorted(list(set(Theater.objects.exclude(city='').values_list('city', flat=True))))
    all_theaters = sorted(list(set(Theater.objects.exclude(name='').values_list('name', flat=True))))[:15]

    query_dict = request.GET.copy()
    if 'page' in query_dict:
        del query_dict['page']
    preserved_query = query_dict.urlencode()

    recommended_movies = get_recommended_movies(request)

    context = {
        'movies': paginated_movies,
        'total_matches': total_matches,
        'recommended_movies': recommended_movies,
        'genres': all_genres,
        'languages': all_languages,
        'cities': all_cities,
        'theaters': all_theaters,
        'search_query': search_query,
        'selected_genre': selected_genre,
        'selected_language': selected_language,
        'selected_city': selected_city,
        'selected_theater': selected_theater,
        'selected_rating': selected_rating,
        'selected_timing': selected_timing,
        'selected_release': selected_release,
        'selected_max_price': selected_max_price,
        'sort_by': sort_by,
        'preserved_query': preserved_query,
    }
    return render(request, 'movies/movie_list.html', context)


def theater_list(request, movie_id):
    """Theater list with city filter and session-tracked recently viewed."""
    movie = get_object_or_404(Movie, id=movie_id)

    recently_viewed = request.session.get('recently_viewed', [])
    if movie_id in recently_viewed:
        recently_viewed.remove(movie_id)
    recently_viewed.insert(0, movie_id)
    request.session['recently_viewed'] = recently_viewed[:10]
    request.session.modified = True

    city_filter = request.GET.get('city', '').strip()
    theaters = Theater.objects.filter(movie=movie)
    if city_filter and city_filter != 'All':
        theaters = theaters.filter(city__iexact=city_filter)
    theaters = theaters.order_by('city', 'time')
    available_cities = sorted(list(set(
        Theater.objects.filter(movie=movie).values_list('city', flat=True)
    )))

    recommended_movies = get_recommended_movies(request, current_movie_id=movie.id)

    return render(request, 'movies/theater_list.html', {
        'movie': movie,
        'theaters': theaters,
        'available_cities': available_cities,
        'selected_city': city_filter,
        'recommended_movies': recommended_movies[:4],
    })


# ════════════════════════════════════════════════
# ════════════════════════════════════════════════
#  TASK 5: Smart Seat Reservation with Live Availability
# ════════════════════════════════════════════════

def live_seat_status(request, theater_id):
    """
    Task 5: Real-time API endpoint returning live seat availability for a theater.
    Automatically cleans up expired reservations and returns current status for each seat.
    """
    theater = get_object_or_404(Theater, id=theater_id)
    release_expired_reservations(theater=theater)

    seats = Seat.objects.filter(theater=theater).order_by('seat_number')
    now = timezone.now()
    current_user = request.user if request.user.is_authenticated else None

    seat_list = []
    for seat in seats:
        status = seat.get_status(current_user=current_user)
        seconds_left = 0
        if seat.reserved_until and seat.reserved_until > now:
            seconds_left = max(0, int((seat.reserved_until - now).total_seconds()))
        seat_list.append({
            'id': seat.id,
            'seat_number': seat.seat_number,
            'status': status,
            'seconds_left': seconds_left,
        })

    return JsonResponse({
        'theater_id': theater.id,
        'seats': seat_list,
        'total_seats': len(seat_list),
        'available_count': sum(1 for s in seat_list if s['status'] == 'available'),
        'reserved_count': sum(1 for s in seat_list if s['status'] in ['reserved', 'selected_by_me']),
        'booked_count': sum(1 for s in seat_list if s['status'] == 'booked'),
        'server_time': now.isoformat(),
    })


@login_required(login_url='/login/')
def book_seats(request, theater_id):
    """
    Seat selection & payment initialization.
    Locks seats with a temporary 2-minute reservation using Django transactions.
    Concurrent booking attempts for the same seats are guarded by select_for_update().
    """
    theaters = get_object_or_404(Theater, id=theater_id)
    # Release any expired reservations for this theater
    release_expired_reservations(theater=theaters)

    seats = Seat.objects.filter(theater=theaters).order_by('seat_number')
    for seat in seats:
        seat.current_status = seat.get_status(request.user)

    error_message = None

    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')
        if not selected_seats:
            error_message = "Please select at least one seat before proceeding to payment."
            return render(request, "movies/seat_selection.html", {
                'theaters': theaters, 'theater': theaters,
                'seats': seats, 'error': error_message
            })

        try:
            with transaction.atomic():
                # Clean up expired reservations under transaction lock
                Seat.objects.filter(
                    theater=theaters,
                    is_booked=False,
                    reserved_until__lte=timezone.now()
                ).update(reserved_by=None, reserved_until=None)

                # Acquire row-level locks on requested seats
                locked_seats = list(
                    Seat.objects.select_for_update().filter(id__in=selected_seats, theater=theaters)
                )

                if len(locked_seats) != len(selected_seats):
                    raise Seat.DoesNotExist("One or more selected seats could not be found.")

                # Check if any seat is already booked or reserved by another patron
                for seat in locked_seats:
                    if not seat.is_available(request.user):
                        raise IntegrityError(f"Seat {seat.seat_number} is no longer available.")

                # Clear previous unconfirmed reservations from this user in this theater
                prev_txns = PaymentTransaction.objects.filter(
                    user=request.user,
                    theater=theaters,
                    status=PaymentTransaction.STATUS_PENDING
                )
                for p_txn in prev_txns:
                    for old_seat in p_txn.seats.select_for_update():
                        if str(old_seat.id) not in selected_seats:
                            old_seat.reserved_by = None
                            old_seat.reserved_until = None
                            old_seat.save(update_fields=['reserved_by', 'reserved_until'])
                    p_txn.status = PaymentTransaction.STATUS_CANCELLED
                    p_txn.error_description = "Superseded by new seat selection"
                    p_txn.save(update_fields=['status', 'error_description', 'updated_at'])

                # Reserve selected seats for 2 minutes (120 seconds)
                reservation_expiry = timezone.now() + timedelta(seconds=120)
                for seat in locked_seats:
                    seat.reserved_by = request.user
                    seat.reserved_until = reservation_expiry
                    seat.is_booked = False
                    seat.save(update_fields=['reserved_by', 'reserved_until', 'is_booked'])

                total_amount = theaters.ticket_price * len(locked_seats)

                # Initialize pending PaymentTransaction
                temp_order_id = f"order_{uuid.uuid4().hex[:14]}"
                payment_txn = PaymentTransaction.objects.create(
                    order_id=temp_order_id,
                    user=request.user,
                    movie=theaters.movie,
                    theater=theaters,
                    amount=total_amount,
                    currency='INR',
                    status=PaymentTransaction.STATUS_PENDING,
                )
                payment_txn.seats.set(locked_seats)

                # Create Razorpay Order
                create_payment_order(payment_txn)

            return redirect('payment_checkout', order_id=payment_txn.order_id)

        except (Seat.DoesNotExist, IntegrityError):
            error_message = "Some selected seats were just reserved or booked by another patron. Please select different seats."
            seats = Seat.objects.filter(theater=theaters).order_by('seat_number')
            for seat in seats:
                seat.current_status = seat.get_status(request.user)
            return render(request, "movies/seat_selection.html", {
                'theaters': theaters, 'theater': theaters,
                'seats': seats, 'error': error_message
            })

    return render(request, 'movies/seat_selection.html', {
        'theaters': theaters, 'theater': theaters, 'seats': seats
    })


@login_required(login_url='/login/')
def modify_seats(request, order_id):
    """
    Task 5: Allows the user to modify seat selection before completing payment.
    Releases all currently held seats immediately and cancels the pending order.
    """
    payment_txn = get_object_or_404(PaymentTransaction, order_id=order_id, user=request.user)
    theater_id = payment_txn.theater.id

    if payment_txn.status == PaymentTransaction.STATUS_PENDING:
        with transaction.atomic():
            for seat in payment_txn.seats.select_for_update():
                seat.reserved_by = None
                seat.reserved_until = None
                seat.is_booked = False
                seat.save(update_fields=['reserved_by', 'reserved_until', 'is_booked'])

            payment_txn.status = PaymentTransaction.STATUS_CANCELLED
            payment_txn.error_description = "User modified seat selection"
            payment_txn.save(update_fields=['status', 'error_description', 'updated_at'])

        messages.info(request, "Your previous seat reservation has been released. You can now select your new seats.")

    return redirect('book_seats', theater_id=theater_id)


# ════════════════════════════════════════════════
#  TASK 4: Payment Workflow & Verification Views
# ════════════════════════════════════════════════

@login_required(login_url='/login/')
def payment_checkout(request, order_id):
    """
    Renders the secure payment checkout screen with Razorpay payment modal,
    live 2-minute countdown timer, and option to modify seat selection.
    """
    payment_txn = get_object_or_404(
        PaymentTransaction.objects.select_related('movie', 'theater'),
        order_id=order_id,
        user=request.user
    )

    # Idempotent redirect if already completed
    if payment_txn.status == PaymentTransaction.STATUS_SUCCESS:
        booking = payment_txn.bookings.first()
        if booking:
            return redirect('booking_confirmation', booking_id=booking.booking_id)

    if payment_txn.status in [PaymentTransaction.STATUS_FAILED, PaymentTransaction.STATUS_CANCELLED]:
        return render(request, 'movies/payment_failed.html', {
            'payment_txn': payment_txn,
            'theater': payment_txn.theater,
            'movie': payment_txn.movie,
            'error_message': f"This transaction was {payment_txn.status.lower()} and seats have been released."
        })

    # Task 5: Verify 2-minute temporary reservation validity
    now = timezone.now()
    seats = list(payment_txn.seats.all().order_by('seat_number'))

    expired = False
    earliest_expiry = None
    for seat in seats:
        if seat.reserved_until:
            if not earliest_expiry or seat.reserved_until < earliest_expiry:
                earliest_expiry = seat.reserved_until
            if seat.reserved_until <= now:
                expired = True
                break
        else:
            expired = True
            break

    if expired:
        process_failed_payment(
            order_id,
            error_code='RESERVATION_EXPIRED',
            error_description='The 2-minute reservation period has expired. Seats were automatically released.'
        )
        messages.warning(request, "Your 2-minute seat reservation expired. Please re-select your seats.")
        return redirect('book_seats', theater_id=payment_txn.theater.id)

    remaining_seconds = max(0, int((earliest_expiry - now).total_seconds())) if earliest_expiry else 120

    seats = payment_txn.seats.all().order_by('seat_number')
    seat_names = ', '.join(s.seat_number for s in seats)
    amount_in_paise = int(payment_txn.amount * 100)

    # Pre-calculated test credentials for simulation mode
    mock_payment_id = f"pay_mock_{uuid.uuid4().hex[:10]}"
    simulation_signature = generate_mock_signature(payment_txn.order_id, mock_payment_id)

    return render(request, 'movies/payment_checkout.html', {
        'payment_txn': payment_txn,
        'theater': payment_txn.theater,
        'movie': payment_txn.movie,
        'seats': seats,
        'seat_names': seat_names,
        'amount_in_paise': amount_in_paise,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'mock_payment_id': mock_payment_id,
        'simulation_signature': simulation_signature,
        'remaining_seconds': remaining_seconds,
    })


@login_required(login_url='/login/')
def payment_verify(request):
    """
    Server-side verification endpoint for Razorpay payment callbacks.
    Verifies HMAC-SHA256 signature and confirms bookings idempotently.
    """
    if request.method != 'POST':
        return redirect('movie_list')

    order_id = request.POST.get('razorpay_order_id', '').strip()
    payment_id = request.POST.get('razorpay_payment_id', '').strip()
    signature = request.POST.get('razorpay_signature', '').strip()
    payment_method = request.POST.get('payment_method', 'Razorpay Online')

    if not order_id or not payment_id or not signature:
        return render(request, 'movies/payment_failed.html', {
            'error_message': 'Incomplete payment parameters received from payment gateway.'
        })

    payment_txn = get_object_or_404(PaymentTransaction, order_id=order_id, user=request.user)

    # Verify signature server-side
    is_valid = verify_payment_signature(order_id, payment_id, signature)

    if not is_valid:
        process_failed_payment(
            order_id,
            error_code='INVALID_SIGNATURE',
            error_description='Server-side HMAC-SHA256 signature verification failed.'
        )
        return render(request, 'movies/payment_failed.html', {
            'payment_txn': payment_txn,
            'theater': payment_txn.theater,
            'movie': payment_txn.movie,
            'error_message': 'Security check failed. The payment signature could not be verified and reserved seats have been released.'
        })

    # Signature valid -> Idempotently confirm bookings and dispatch tickets
    bookings = process_successful_payment(order_id, payment_id, payment_method)
    if bookings:
        return redirect('booking_confirmation', booking_id=bookings[0].booking_id)

    return redirect('profile')


@login_required(login_url='/login/')
def payment_failed(request):
    """
    Handles payment failure callbacks.
    Ensures reserved seats are automatically released.
    """
    order_id = request.GET.get('order_id') or request.POST.get('order_id')
    error_code = request.GET.get('error_code') or request.POST.get('error_code', 'PAYMENT_FAILED')
    error_desc = request.GET.get('error_desc') or request.POST.get('error_desc', 'The transaction was declined or failed.')

    payment_txn = None
    if order_id:
        payment_txn = PaymentTransaction.objects.filter(order_id=order_id, user=request.user).first()
        if payment_txn:
            process_failed_payment(order_id, error_code, error_desc)

    return render(request, 'movies/payment_failed.html', {
        'payment_txn': payment_txn,
        'theater': payment_txn.theater if payment_txn else None,
        'movie': payment_txn.movie if payment_txn else None,
        'error_message': error_desc,
    })


@login_required(login_url='/login/')
def payment_cancel(request, order_id):
    """
    User manually cancelled the payment.
    Automatically releases reserved seats and redirects to seat selection.
    """
    payment_txn = get_object_or_404(PaymentTransaction, order_id=order_id, user=request.user)
    theater_id = payment_txn.theater.id
    process_cancelled_payment(order_id)
    return redirect('book_seats', theater_id=theater_id)


@csrf_exempt
def payment_webhook(request):
    """
    Server-side webhook listener for Razorpay asynchronous events.
    Verifies X-Razorpay-Signature header and idempotently processes event.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    signature_header = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')
    body = request.body

    if not verify_webhook_signature(body, signature_header):
        return JsonResponse({'error': 'Invalid webhook signature'}, status=400)

    try:
        import json
        payload = json.loads(body.decode('utf-8'))
        event = payload.get('event')
        entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = entity.get('order_id')
        payment_id = entity.get('id')
        method = entity.get('method', 'Webhook')

        if event in ['payment.captured', 'order.paid'] and order_id:
            process_successful_payment(order_id, payment_id, method)
        elif event == 'payment.failed' and order_id:
            error_code = entity.get('error_code', 'WEBHOOK_FAILED')
            error_desc = entity.get('error_description', 'Payment failed via webhook notification')
            process_failed_payment(order_id, error_code, error_desc)

        return JsonResponse({'status': 'processed', 'event': event})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required(login_url='/login/')
def booking_confirmation(request, booking_id):
    """Show booking confirmation with ticket details after successful booking."""
    ref_booking = get_object_or_404(
        Booking, booking_id=booking_id, user=request.user
    )
    # Get all bookings in the same transaction
    if ref_booking.payment:
        related_bookings = Booking.objects.filter(
            payment=ref_booking.payment
        ).select_related('seat', 'movie', 'theater').order_by('seat__seat_number')
    else:
        related_bookings = Booking.objects.filter(
            user=request.user,
            movie=ref_booking.movie,
            theater=ref_booking.theater,
            booked_at=ref_booking.booked_at,
        ).select_related('seat', 'movie', 'theater').order_by('seat__seat_number')


    seat_numbers = ', '.join(b.seat.seat_number for b in related_bookings)
    total_price = ref_booking.theater.ticket_price * related_bookings.count()

    return render(request, 'movies/booking_confirmation.html', {
        'booking': ref_booking,
        'bookings': related_bookings,
        'seat_numbers': seat_numbers,
        'total_price': total_price,
        'ticket_count': related_bookings.count(),
    })


@login_required(login_url='/login/')
def download_ticket(request, booking_id):
    """Download a previously generated PDF ticket."""
    booking = get_object_or_404(
        Booking, booking_id=booking_id, user=request.user
    )

    if booking.ticket_pdf:
        try:
            file_path = booking.ticket_pdf.path
            if os.path.exists(file_path):
                return FileResponse(
                    open(file_path, 'rb'),
                    content_type='application/pdf',
                    as_attachment=True,
                    filename=f'BookMySeat_Ticket_{str(booking_id)[:8].upper()}.pdf',
                )
        except Exception:
            pass

    # If PDF doesn't exist yet or in serverless environment, generate it on the fly
    from movies.ticket_utils import generate_ticket_pdf

    related_bookings = list(
        Booking.objects.filter(
            user=request.user, movie=booking.movie,
            theater=booking.theater, booked_at=booking.booked_at,
        ).select_related('seat', 'movie', 'theater').order_by('seat__seat_number')
    )

    pdf_buffer = generate_ticket_pdf(related_bookings, request.user)
    return FileResponse(
        pdf_buffer,
        content_type='application/pdf',
        as_attachment=True,
        filename=f'BookMySeat_Ticket_{str(booking_id)[:8].upper()}.pdf',
    )


# ════════════════════════════════════════════════
#  TASK 3: Movie Details, Trailer, Reviews
# ════════════════════════════════════════════════

def update_movie_rating(movie):
    """Recalculate and update the movie rating based on all reviews."""
    reviews = movie.reviews.all()
    if reviews.exists():
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        movie.rating = round(avg_rating, 1)
    else:
        movie.rating = 8.0 # Default
    movie.save()

def movie_detail(request, movie_id):
    """
    Display movie details: Trailer, Gallery, Reviews, Recommendations.
    Only allows authenticated users who have already watched to submit a review.
    """
    movie = get_object_or_404(Movie, id=movie_id)

    # Track recently viewed movie in session for recommendations
    recently_viewed = request.session.get('recently_viewed', [])
    if movie_id in recently_viewed:
        recently_viewed.remove(movie_id)
    recently_viewed.insert(0, movie_id)
    request.session['recently_viewed'] = recently_viewed[:10]
    request.session.modified = True

    gallery = movie.gallery.all()
    reviews = movie.reviews.all().order_by('-created_at')
    
    can_review = False
    user_review = None
    
    if request.user.is_authenticated:
        # Check if they have a past booking (time < now)
        past_bookings = Booking.objects.filter(
            user=request.user,
            movie=movie,
            theater__time__lt=timezone.now()
        )
        if past_bookings.exists():
            can_review = True
            
        # Get their existing review if any
        user_review = reviews.filter(user=request.user).first()
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'submit_review' and can_review:
            rating = int(request.POST.get('rating', 10))
            text = request.POST.get('review_text', '').strip()
            
            if user_review:
                user_review.rating = rating
                user_review.review_text = text
                user_review.save()
            else:
                Review.objects.create(
                    movie=movie,
                    user=request.user,
                    rating=rating,
                    review_text=text,
                    verified_viewer=True
                )
            update_movie_rating(movie)
            return redirect('movie_detail', movie_id=movie.id)
            
        elif action == 'report_review' and request.user.is_authenticated:
            review_id = request.POST.get('review_id')
            try:
                rep_rev = Review.objects.get(id=review_id, movie=movie)
                rep_rev.is_reported = True
                rep_rev.save()
            except Review.DoesNotExist:
                pass
            return redirect('movie_detail', movie_id=movie.id)

    # Similar movies based on shared genres
    similar_movies = Movie.objects.filter(genres__in=movie.genres.all()).exclude(id=movie.id).distinct().order_by('-popularity')[:4]
    
    # Fallback to trending if no similar movies found
    if not similar_movies.exists():
        similar_movies = Movie.objects.exclude(id=movie.id).order_by('-rating', '-popularity')[:4]

    primary_theater = movie.theaters.order_by('time').first()

    context = {
        'movie': movie,
        'gallery': gallery,
        'reviews': reviews,
        'can_review': can_review,
        'user_review': user_review,
        'similar_movies': similar_movies,
        'primary_theater': primary_theater,
    }
    return render(request, 'movies/movie_detail.html', context)

