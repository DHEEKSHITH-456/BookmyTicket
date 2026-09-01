from django.contrib import admin
from .models import Movie, Theater, Seat, Booking


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['name', 'rating', 'genre', 'language', 'release_date', 'duration', 'popularity']
    list_filter = ['genre', 'language', 'release_date']
    search_fields = ['name', 'cast', 'genre', 'description']


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'movie', 'ticket_price', 'time']
    list_filter = ['city', 'movie']
    search_fields = ['name', 'city', 'location']


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'is_booked']
    list_filter = ['is_booked']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'user', 'movie', 'theater', 'seat', 'payment_reference', 'email_sent', 'booked_at']
    list_filter = ['email_sent', 'booked_at']
    search_fields = ['booking_id', 'payment_reference', 'user__username']
    readonly_fields = ['booking_id', 'payment_reference']
