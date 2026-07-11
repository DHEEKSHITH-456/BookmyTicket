from django.db import models
from django.contrib.auth.models import User

class Movie(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='movie_images/')
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    cast = models.TextField(help_text="Comma-separated list of cast members")
    description = models.TextField(blank=True,null=True)
    release_date = models.DateField()
    duration = models.IntegerField(help_text="Duration in minutes")
    genre = models.CharField(max_length=50)

    def __str__(self):
        return self.name
class Theater(models.Model):
    name = models.CharField(max_length=100)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='theaters')
    time = models.TimeField()
    location = models.CharField(max_length=200)
    capacity = models.IntegerField(help_text="Total number of seats in the theater")
    def __str__(self):
        return f"{self.name} - {self.movie.name} at {self.time}"  
class Seat(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f"Seat {self.seat_number} in {self.theater.name} "  
class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='bookings')
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='bookings')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='bookings')
    booking_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking by {self.user.username} for {self.theater.movie.name} at {self.theater.time}"
