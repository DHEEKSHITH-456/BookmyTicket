import uuid
from django.db import models
from django.contrib.auth.models import User


class Movie(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="movies/")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=8.0)
    genre = models.CharField(max_length=100, default='Action', help_text="Comma-separated genres, e.g. Action, Sci-Fi")
    language = models.CharField(max_length=50, default='English')
    release_date = models.DateField(null=True, blank=True)
    duration = models.IntegerField(default=120, help_text="Duration in minutes")
    popularity = models.IntegerField(default=100, help_text="Popularity / Votes count")
    cast = models.TextField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Theater(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100, default='Hyderabad')
    location = models.CharField(max_length=255, blank=True, null=True)
    ticket_price = models.DecimalField(max_digits=6, decimal_places=2, default=200.00)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='theaters')
    time = models.DateTimeField()

    def __str__(self):
        return f'{self.name} ({self.city}) - {self.movie.name} at {self.time}'


class Seat(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    seat = models.OneToOneField(Seat, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='bookings')
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='bookings')
    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    payment_reference = models.CharField(max_length=20, blank=True, null=True)
    ticket_pdf = models.FileField(upload_to='tickets/', blank=True, null=True)
    email_sent = models.BooleanField(default=False)
    booked_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.payment_reference:
            self.payment_reference = f'PAY-{uuid.uuid4().hex[:12].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Booking {self.booking_id} by {self.user.username} for {self.seat.seat_number} at {self.theater.name}'