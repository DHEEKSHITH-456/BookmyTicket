from django.contrib import admin
from .models import Movie, Theater, Seat, Booking

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating', 'release_date', 'genre')
    search_fields = ('name', 'genre')
    list_filter = ('genre', 'release_date')
@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ('name', 'movie', 'time', 'location', 'capacity')
    search_fields = ('name', 'location')
    list_filter = ('movie', 'time')
@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):  
    list_display = ('theater', 'seat_number', 'is_booked')
    search_fields = ('theater__name', 'seat_number')
    list_filter = ('is_booked',)
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'theater', 'seat', 'booking_time')
    search_fields = ('user__username', 'movie__name', 'theater__name')
    list_filter = ('booking_time',)
