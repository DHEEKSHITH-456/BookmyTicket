import os
import sys
import django

# Setup Django Environment
sys.path.insert(0, r"d:\Intership project\django-bookmyshow-clone")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from django.test.utils import setup_test_environment
setup_test_environment()

from django.test import Client
from django.contrib.auth.models import User
from django.contrib import admin
from django.utils import timezone
from datetime import timedelta

from movies.models import Movie, MovieImage, Genre, Language, CastMember, Theater, Seat, Booking, Review
from movies.views import update_movie_rating

def run_tests():
    print("=" * 75)
    print("   TASK 3: MOVIE MANAGEMENT, TRAILERS, REVIEWS & RATINGS AUDIT   ")
    print("=" * 75)

    client = Client()

    # -------------------------------------------------------------
    # [1] Django Admin Registrations & Inlines
    # -------------------------------------------------------------
    print("\n[1] Testing Django Admin Model Registrations & Inlines...")
    registered_models = admin.site._registry
    required_models = [Movie, Genre, Language, CastMember, Theater, Seat, Review, Booking]
    
    for model in required_models:
        assert model in registered_models, f"{model.__name__} is NOT registered in Django admin!"
    
    movie_admin = registered_models[Movie]
    inline_models = [inline.model for inline in movie_admin.inlines]
    assert MovieImage in inline_models, "MovieImageInline missing from MovieAdmin inlines!"
    print("  [PASS] 1: All required models registered with MovieImageInline gallery support")

    # -------------------------------------------------------------
    # [2] Movie Schema: Trailers, Age Certification, Duration, Descriptions
    # -------------------------------------------------------------
    print("\n[2] Testing Movie Schema, Media Attributes & Secure Trailer Embed...")
    g_action, _ = Genre.objects.get_or_create(name='Action')
    lang_en, _ = Language.objects.get_or_create(name='English')
    cast_lead, _ = CastMember.objects.get_or_create(name='Christopher Nolan')

    movie = Movie.objects.create(
        name='Task3 Cinematic Showcase',
        rating=8.0,
        age_certification='U/A',
        duration=148,
        description='An epic cinematic masterpiece demonstrating movie management.',
        release_date=timezone.now().date() - timedelta(days=10),
        trailer_url='https://www.youtube.com/watch?v=YoHD9XEInc0',
    )
    movie.genres.add(g_action)
    movie.languages.add(lang_en)
    movie.cast_members.add(cast_lead)

    # Test secure embed property
    assert movie.youtube_embed_url == 'https://www.youtube-nocookie.com/embed/YoHD9XEInc0', \
        f"youtube_embed_url failed to convert: {movie.youtube_embed_url}"
    
    # Test shortened URL conversion
    movie.trailer_url = 'https://youtu.be/YoHD9XEInc0'
    assert movie.youtube_embed_url == 'https://www.youtube-nocookie.com/embed/YoHD9XEInc0'
    print(f"  [PASS] 2: Schema validated (Age: {movie.age_certification}, Duration: {movie.duration}m, Secure Embed: {movie.youtube_embed_url})")

    # -------------------------------------------------------------
    # [3] Verified Viewer Review Gate (Must Book & Watch)
    # -------------------------------------------------------------
    print("\n[3] Testing Verified Viewer Review Restriction (Booking Gate)...")
    patron, _ = User.objects.get_or_create(username='t3_patron', defaults={'email': 't3_patron@example.com'})
    patron.set_password('pass123')
    patron.save()

    outsider, _ = User.objects.get_or_create(username='t3_outsider', defaults={'email': 't3_outsider@example.com'})
    outsider.set_password('pass123')
    outsider.save()

    # Patron hasn't watched movie yet -> cannot review
    client.login(username='t3_patron', password='pass123')
    res_before = client.get(f'/movies/movie/{movie.id}/')
    assert res_before.context['can_review'] is False, "User should NOT be able to review without booking!"

    # Create past theater screening and booking for patron
    theater = Theater.objects.create(
        name='PVR Central Mall',
        movie=movie,
        city='Hyderabad',
        ticket_price=220.00,
        time=timezone.now() - timedelta(days=1), # Showtime occurred yesterday
    )
    seat = Seat.objects.create(theater=theater, seat_number='T3-VIP', is_booked=True)
    booking = Booking.objects.create(user=patron, movie=movie, theater=theater, seat=seat)

    # Now patron has booked and watched the movie
    res_after = client.get(f'/movies/movie/{movie.id}/')
    assert res_after.context['can_review'] is True, "User who booked and watched movie SHOULD be able to review!"
    print("  [PASS] 3: Verified Viewer review gate strictly enforced (unbooked patrons blocked, watchers allowed)")

    # -------------------------------------------------------------
    # [4] Review Submission & Automatic Dynamic Rating Recalculation
    # -------------------------------------------------------------
    print("\n[4] Testing Review Submission & Dynamic Rating Calculation...")
    res_post = client.post(f'/movies/movie/{movie.id}/', {
        'action': 'submit_review',
        'rating': '10',
        'review_text': 'Phenomenal film with breathtaking visuals!',
    })
    assert res_post.status_code == 302, f"Expected redirect, got {res_post.status_code}"
    
    review1 = Review.objects.get(movie=movie, user=patron)
    assert review1.verified_viewer is True, "Review must be marked verified_viewer=True"
    assert review1.rating == 10
    
    movie.refresh_from_db()
    assert float(movie.rating) == 10.0, f"Movie rating should be 10.0, found {movie.rating}"
    print(f"  [PASS] 4: Review submitted with verified badge and dynamic movie rating updated to {movie.rating}")

    # -------------------------------------------------------------
    # [5] Review Editing (In-Place Update & Recalculation)
    # -------------------------------------------------------------
    print("\n[5] Testing Review In-Place Editing...")
    client.post(f'/movies/movie/{movie.id}/', {
        'action': 'submit_review',
        'rating': '6',
        'review_text': 'Rewatched and found the pacing uneven in the second act.',
    })
    review1.refresh_from_db()
    assert review1.rating == 6, f"Expected edited rating 6, got {review1.rating}"
    assert 'uneven' in review1.review_text
    
    movie.refresh_from_db()
    assert float(movie.rating) == 6.0, f"Expected recalculated rating 6.0, got {movie.rating}"
    print(f"  [PASS] 5: Review edited and movie rating recalculated to {movie.rating}")

    # -------------------------------------------------------------
    # [6] Community Moderation: Reporting Inappropriate Content
    # -------------------------------------------------------------
    print("\n[6] Testing Community Moderation (Report Review)...")
    client.login(username='t3_outsider', password='pass123')
    res_report = client.post(f'/movies/movie/{movie.id}/', {
        'action': 'report_review',
        'review_id': review1.id,
    })
    assert res_report.status_code == 302
    review1.refresh_from_db()
    assert review1.is_reported is True, "Review should be flagged as is_reported=True"
    print("  [PASS] 6: Community review reporting operational (is_reported=True)")

    # -------------------------------------------------------------
    # [7] Movie Detail Recommendations (Similar, Trending, Recent)
    # -------------------------------------------------------------
    print("\n[7] Testing Recommendations on Movie Detail Page...")
    # Create companion movies with high popularity to rank in top 4
    m_sim = Movie.objects.create(name='Similar Action Film', rating=8.5, popularity=99999)
    m_sim.genres.add(g_action)

    m_trend = Movie.objects.create(name='Trending Sci-Fi Film', rating=9.0, popularity=88888)
    m_recent = Movie.objects.create(
        name='Brand New Premiere',
        rating=7.8,
        popularity=77777,
        release_date=timezone.now().date()
    )

    res_detail = client.get(f'/movies/{movie.id}/')
    ctx = res_detail.context
    assert 'similar_movies' in ctx, "similar_movies missing from context"
    assert 'trending_movies' in ctx, "trending_movies missing from context"
    assert 'recent_movies' in ctx, "recent_movies missing from context"

    assert m_sim in ctx['similar_movies'], "Similar movie by genre/language not found in similar_movies"
    assert movie not in ctx['similar_movies'], "Current movie must not appear in its own similar recommendations"
    assert movie not in ctx['trending_movies'], "Current movie must not appear in trending recommendations"
    print("  [PASS] 7: Similar movies (genre/language), trending, and recent recommendations rendered")

    # -------------------------------------------------------------
    # Cleanup Test Records
    # -------------------------------------------------------------
    review1.delete()
    booking.delete()
    seat.delete()
    theater.delete()
    movie.delete()
    m_sim.delete()
    m_trend.delete()
    m_recent.delete()
    patron.delete()
    outsider.delete()

    print("\n" + "=" * 75)
    print("     ALL 7 TASK 3 ACCEPTANCE CRITERIA ARE 100% VERIFIED!      ")
    print("=" * 75)

if __name__ == '__main__':
    run_tests()
