import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Language(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class CastMember(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self): return self.name

class Movie(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="movies/")
    trailer_url = models.URLField(blank=True, null=True, help_text="YouTube embed URL")
    
    AGE_CHOICES = (
        ('U', 'U (Unrestricted Public Exhibition)'),
        ('U/A', 'U/A (Parental Guidance for children below 12)'),
        ('A', 'A (Adults Only)'),
        ('S', 'S (Specialized Audience)'),
    )
    age_certification = models.CharField(max_length=5, choices=AGE_CHOICES, default='U/A')
    
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=8.0)
    
    # New M2M relationships
    genres = models.ManyToManyField(Genre, blank=True)
    languages = models.ManyToManyField(Language, blank=True)
    cast_members = models.ManyToManyField(CastMember, blank=True)
    
    release_date = models.DateField(null=True, blank=True)
    duration = models.IntegerField(default=120, help_text="Duration in minutes")
    popularity = models.IntegerField(default=100, help_text="Popularity / Votes count")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class MovieImage(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to="movies/gallery/")
    
    def __str__(self):
        return f"Image for {self.movie.name}"

class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(default=10, help_text="Rating 1-10")
    review_text = models.TextField()
    verified_viewer = models.BooleanField(default=False)
    is_reported = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('movie', 'user')
        
    def __str__(self):
        return f"Review by {self.user.username} for {self.movie.name}"


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
    reserved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reserved_seats')
    reserved_until = models.DateTimeField(null=True, blank=True, db_index=True)

    def is_available(self, current_user=None):
        """Returns True if seat can be reserved or booked by current_user."""
        now = timezone.now()
        if self.is_booked:
            return False
        if self.reserved_until and self.reserved_until > now:
            if current_user and self.reserved_by_id == current_user.id:
                return True
            return False
        return True

    def get_status(self, current_user=None):
        """Returns: 'booked', 'reserved', 'selected_by_me', or 'available'."""
        now = timezone.now()
        if self.is_booked:
            return 'booked'
        if self.reserved_until and self.reserved_until > now:
            if current_user and self.reserved_by_id == current_user.id:
                return 'selected_by_me'
            return 'reserved'
        return 'available'

    class Meta:
        indexes = [
            models.Index(fields=['theater', 'is_booked'], name='seat_theater_booked_idx'),
        ]

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'


class PaymentTransaction(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAILED = 'FAILED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_REFUNDED = 'REFUNDED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order_id = models.CharField(max_length=100, unique=True, db_index=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_transactions')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='payment_transactions')
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='payment_transactions')
    seats = models.ManyToManyField(Seat, related_name='payment_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    error_code = models.CharField(max_length=100, blank=True, null=True)
    error_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at'], name='pay_created_at_idx'),
            models.Index(fields=['status', 'created_at'], name='pay_status_created_idx'),
            models.Index(fields=['user', 'created_at'], name='pay_user_created_idx'),
        ]

    def __str__(self):
        return f'Txn {self.transaction_id} ({self.status}) - ₹{self.amount} by {self.user.username}'


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    seat = models.OneToOneField(Seat, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='bookings')
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='bookings')
    payment = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    ticket_pdf = models.FileField(upload_to='tickets/', blank=True, null=True)
    email_sent = models.BooleanField(default=False)
    booked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-booked_at']
        indexes = [
            models.Index(fields=['booked_at'], name='booking_booked_at_idx'),
            models.Index(fields=['theater', 'booked_at'], name='booking_theater_date_idx'),
            models.Index(fields=['movie', 'booked_at'], name='booking_movie_date_idx'),
            models.Index(fields=['user', 'booked_at'], name='booking_user_date_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.payment_reference:
            self.payment_reference = f'PAY-{uuid.uuid4().hex[:12].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Booking {self.booking_id} by {self.user.username} for {self.seat.seat_number} at {self.theater.name}'