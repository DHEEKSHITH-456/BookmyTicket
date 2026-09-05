from django.contrib import admin
from .models import Movie, Theater, Seat, Booking, Genre, Language, CastMember, MovieImage, Review, PaymentTransaction

class MovieImageInline(admin.TabularInline):
    model = MovieImage
    extra = 1

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['name', 'rating', 'get_genres', 'get_languages', 'release_date', 'duration', 'popularity']
    list_filter = ['genres', 'languages', 'release_date']
    search_fields = ['name', 'cast_members__name', 'genres__name', 'description']
    inlines = [MovieImageInline]
    
    def get_genres(self, obj):
        return ", ".join([g.name for g in obj.genres.all()])
    get_genres.short_description = 'Genres'

    def get_languages(self, obj):
        return ", ".join([l.name for l in obj.languages.all()])
    get_languages.short_description = 'Languages'

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(CastMember)
class CastMemberAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['movie', 'user', 'rating', 'verified_viewer', 'is_reported', 'created_at']
    list_filter = ['verified_viewer', 'is_reported', 'rating']
    search_fields = ['movie__name', 'user__username', 'review_text']
    

@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'movie', 'ticket_price', 'time']
    list_filter = ['city', 'movie']
    search_fields = ['name', 'city', 'location']


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'is_booked']
    list_filter = ['is_booked']


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'order_id', 'payment_id', 'user', 'movie', 'amount', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['transaction_id', 'order_id', 'payment_id', 'user__username', 'movie__name']
    readonly_fields = ['transaction_id', 'created_at', 'updated_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'user', 'movie', 'theater', 'seat', 'payment_reference', 'email_sent', 'booked_at']
    list_filter = ['email_sent', 'booked_at']
    search_fields = ['booking_id', 'payment_reference', 'user__username']
    readonly_fields = ['booking_id', 'payment_reference']

