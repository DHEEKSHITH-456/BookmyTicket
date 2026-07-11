from django.shortcuts import get_object_or_404, redirect, render
from .models import Movie, Theater, Seat, Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

def movie_list(request):
    search_query = request.GET.get('search', '')
    if search_query:
        movies = Movie.objects.filter(name__icontains=search_query)
    else:
        movies = Movie.objects.all()
    return render(request, 'movies/movie_list.html', {'movies': movies})


def home(request):
    search_query = request.GET.get('search', '')
    if search_query:
        movies = Movie.objects.filter(name__icontains=search_query)
    else:
        movies = Movie.objects.all()
    return render(request, 'home.html', {'movies': movies})


def theater_list(request, movie_id):
    movies = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie_id=movie_id)
    return render(request, 'movies/theater_list.html', {'movie': movies, 'theaters': theaters})

@login_required(login_url='/login/')
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
            error_seats = []
            for seat_id in selected_seats:
                try:
                    seat = Seat.objects.get(id=seat_id, theater_id=theater_id, is_booked=False)
                    seat.is_booked = True
                    seat.save()
                    Booking.objects.create(
                        user=request.user,
                        movie=theater.movie,
                        theater=theater,
                        seat=seat
                    )
                except Seat.DoesNotExist:
                    error_seats.append(seat_id)
                except IntegrityError:
                    error_seats.append(seat_id)

            if error_seats:
                error_message = (
                    'Some selected seats are already booked. Please refresh the page and select different seats.'
                )
            else:
                return redirect('profile')

    return render(request, 'movies/seat_selection.html', {
        'theater': theater,
        'seats': seats,
        'selected_seats': selected_seats,
        'error_message': error_message,
    })