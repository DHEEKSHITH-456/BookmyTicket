import os
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q, Min, Max, Count, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import FileResponse, Http404
from django.conf import settings
from django.utils import timezone
from .models import Movie, Theater, Seat, Booking, Review


# ════════════════════════════════════════════════
#  TASK 1: Recommendation Engine
# ════════════════════════════════════════════════

def get_recommended_movies(request, current_movie_id=None):
    """
    Intelligent recommendation engine based on:
    1. User's past booking history (favorite genres and languages)
    2. User's recently viewed movies stored in session
    3. Fallback to top-rated & most popular movies
    """
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

            rec_qs = Movie.objects.exclude(id__in=booked_movie_ids)
            if current_movie_id:
                rec_qs = rec_qs.exclude(id=current_movie_id)

            history_recs = rec_qs.filter(
                genre_query | Q(languages__name__in=favorite_languages)
            ).order_by('-rating', '-popularity')[:6]
            if history_recs.exists():
                for m in history_recs:
                    m.rec_badge = "Based on your booking history"
                return list(history_recs)

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

        rec_qs = Movie.objects.exclude(id__in=recently_viewed_ids)
        if current_movie_id:
            rec_qs = rec_qs.exclude(id=current_movie_id)

        view_recs = rec_qs.filter(genre_q).order_by('-rating', '-popularity')[:6]
        if view_recs.exists():
            for m in view_recs:
                m.rec_badge = "Because you recently viewed similar movies"
            return list(view_recs)

    # 3. Fallback: Trending & Top Rated Movies
    rec_qs = Movie.objects.all()
    if current_movie_id:
        rec_qs = rec_qs.exclude(id=current_movie_id)

    top_recs = rec_qs.order_by('-rating', '-popularity')[:6]
    for m in top_recs:
        m.rec_badge = "Trending & Highest Rated"
    return list(top_recs)


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
    selected_timing = request.GET.get('timing', '').strip()
    selected_release = request.GET.get('release', '').strip()
    selected_max_price = request.GET.get('max_price', '').strip()
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

    if selected_max_price:
        try:
            movies = movies.filter(theaters__ticket_price__lte=float(selected_max_price))
        except ValueError:
            pass

    movies = movies.distinct()

    if sort_by == 'newest':
        movies = movies.order_by('-release_date', '-id')
    elif sort_by == 'rating':
        movies = movies.order_by('-rating', '-popularity')
    elif sort_by == 'price_asc':
        movies = movies.order_by('min_ticket_price', '-rating')
    elif sort_by == 'price_desc':
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
#  TASK 2: Booking with Ticket Generation & Email
# ════════════════════════════════════════════════

@login_required(login_url='/login/')
def book_seats(request, theater_id):
    """
    Book seats, generate PDF ticket, and trigger async email via Celery.
    The booking completes immediately — email is sent in the background.
    """
    theaters = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater=theaters).order_by('seat_number')
    error_message = None

    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')
        if not selected_seats:
            error_message = "Please select at least one seat before booking."
            return render(request, "movies/seat_selection.html", {
                'theaters': theaters, 'theater': theaters,
                'seats': seats, 'error': error_message
            })

        try:
            created_bookings = []
            with transaction.atomic():
                for seat_id in selected_seats:
                    seat = Seat.objects.select_for_update().get(
                        id=seat_id, theater=theaters, is_booked=False
                    )
                    seat.is_booked = True
                    seat.save()
                    booking = Booking.objects.create(
                        user=request.user,
                        seat=seat,
                        movie=theaters.movie,
                        theater=theaters
                    )
                    created_bookings.append(booking)

            # Trigger async ticket generation + email (never blocks booking)
            try:
                from movies.tasks import generate_and_email_ticket
                booking_ids = [b.pk for b in created_bookings]
                generate_and_email_ticket.delay(booking_ids, request.user.pk)
            except Exception as task_err:
                pass

            return redirect('booking_confirmation', booking_id=created_bookings[0].booking_id)

        except (Seat.DoesNotExist, IntegrityError):
            error_message = "Some selected seats are already booked. Please choose different seats."
            return render(request, "movies/seat_selection.html", {
                'theaters': theaters, 'theater': theaters,
                'seats': seats, 'error': error_message
            })

    return render(request, 'movies/seat_selection.html', {
        'theaters': theaters, 'theater': theaters, 'seats': seats
    })


@login_required(login_url='/login/')
def booking_confirmation(request, booking_id):
    """Show booking confirmation with ticket details after successful booking."""
    ref_booking = get_object_or_404(
        Booking, booking_id=booking_id, user=request.user
    )
    # Get all bookings in the same transaction (same user, movie, theater, close timestamp)
    related_bookings = Booking.objects.filter(
        user=request.user,
        movie=ref_booking.movie,
        theater=ref_booking.theater,
        booked_at=ref_booking.booked_at,
    ).select_related('seat', 'movie', 'theater')

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

    context = {
        'movie': movie,
        'gallery': gallery,
        'reviews': reviews,
        'can_review': can_review,
        'user_review': user_review,
        'similar_movies': similar_movies,
    }
    return render(request, 'movies/movie_detail.html', context)

