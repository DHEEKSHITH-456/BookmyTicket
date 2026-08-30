from django.shortcuts import get_object_or_404, redirect, render
from .models import Movie, Theater, Seat, Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction

def movie_list(request):
    search_query = request.GET.get('search', '')
    genre_query = request.GET.get('genre', '')
    movies = Movie.objects.all()
    if search_query:
        movies = movies.filter(name__icontains=search_query)
    if genre_query and genre_query != 'All':
        movies = movies.filter(genre__icontains=genre_query)
    return render(request, 'movies/movie_list.html', {
        'movies': movies,
        'selected_genre': genre_query
    })


def home(request):
    search_query = request.GET.get('search', '')
    movies = Movie.objects.all()
    if search_query:
        movies = movies.filter(name__icontains=search_query)
    return render(request, 'home.html', {'movies': movies})


def theater_list(request, movie_id):
    movies = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie_id=movie_id)
    return render(request, 'movies/theater_list.html', {'movie': movies, 'theaters': theaters})

@login_required
def seat_selection(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater_id=theater_id)
    selected_seats = []
    error_message = None

    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')
        if not selected_seats:
            error_message = 'Please select at least one seat before booking.'
        else:
            try:
                with transaction.atomic():
                    for seat_id in selected_seats:
                        seat = Seat.objects.select_for_update().get(id=seat_id, theater_id=theater_id, is_booked=False)
                        seat.is_booked = True
                        seat.save()
                        Booking.objects.create(
                            user=request.user,
                            movie=theater.movie,
                            theater=theater,
                            seat=seat
                        )
                return redirect('profile')
            except (Seat.DoesNotExist, IntegrityError):
                error_message = (
                    'Some selected seats are already booked. Please refresh the page and select different seats.'
                )

    return render(request, 'movies/seat_selection.html', {
        'theater': theater,
        'seats': seats,
        'selected_seats': selected_seats,
        'error_message': error_message,
    })