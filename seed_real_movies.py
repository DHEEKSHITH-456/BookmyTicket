import os
import django
from urllib.request import Request, urlopen
from django.core.files import File
from django.utils import timezone
from datetime import timedelta
import tempfile
import urllib.error

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from movies.models import Movie, Theater, Seat

new_movies = [
    {
        'name': 'The Dark Knight',
        'url': 'https://upload.wikimedia.org/wikipedia/en/1/1c/The_Dark_Knight_%282008_film%29.jpg',
        'genre': 'Action, Thriller',
        'rating': 9.0,
        'duration': 152,
        'cast': 'Christian Bale, Heath Ledger, Aaron Eckhart',
        'desc': 'When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.'
    },
    {
        'name': 'Inception',
        'url': 'https://upload.wikimedia.org/wikipedia/en/2/2e/Inception_%282010%29_theatrical_poster.jpg',
        'genre': 'Action, Sci-Fi',
        'rating': 8.8,
        'duration': 148,
        'cast': 'Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page',
        'desc': 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.'
    },
    {
        'name': 'Interstellar',
        'url': 'https://upload.wikimedia.org/wikipedia/en/b/bc/Interstellar_film_poster.jpg',
        'genre': 'Adventure, Sci-Fi',
        'rating': 8.7,
        'duration': 169,
        'cast': 'Matthew McConaughey, Anne Hathaway, Jessica Chastain',
        'desc': 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity\'s survival.'
    },
    {
        'name': 'Avatar',
        'url': 'https://upload.wikimedia.org/wikipedia/en/d/d6/Avatar_%282009_film%29_poster.jpg',
        'genre': 'Action, Adventure, Fantasy',
        'rating': 7.9,
        'duration': 162,
        'cast': 'Sam Worthington, Zoe Saldana, Sigourney Weaver',
        'desc': 'A paraplegic Marine dispatched to the moon Pandora on a unique mission becomes torn between following his orders and protecting the world he feels is his home.'
    },
    {
        'name': 'The Matrix',
        'url': 'https://upload.wikimedia.org/wikipedia/en/c/c1/The_Matrix_Poster.jpg',
        'genre': 'Action, Sci-Fi',
        'rating': 8.7,
        'duration': 136,
        'cast': 'Keanu Reeves, Laurence Fishburne, Carrie-Anne Moss',
        'desc': 'When a beautiful stranger leads computer hacker Neo to a forbidding underworld, he discovers the shocking truth--the life he knows is the elaborate deception of an evil cyber-intelligence.'
    }
]

os.makedirs('media/movies', exist_ok=True)

def download_image(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    fd, path = tempfile.mkstemp(suffix=".jpg")
    try:
        with urlopen(req) as response:
            with open(path, 'wb') as out_file:
                out_file.write(response.read())
        return path
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None

for m_data in new_movies:
    # Remove old version if exists to update image
    if Movie.objects.filter(name=m_data['name']).exists():
        Movie.objects.filter(name=m_data['name']).delete()
        print(f"Deleted existing movie: {m_data['name']}")
        
    print(f"Adding movie: {m_data['name']}")
    
    tmp_img = download_image(m_data['url'])
    if not tmp_img:
        continue
    
    movie = Movie.objects.create(
        name=m_data['name'],
        genre=m_data['genre'],
        rating=m_data['rating'],
        duration=m_data['duration'],
        cast=m_data['cast'],
        description=m_data['desc'],
        popularity=150,
        release_date=timezone.now().date(),
        language='English'
    )
    
    with open(tmp_img, 'rb') as f:
        movie.image.save(f"{m_data['name'].replace(' ', '_').lower()}.jpg", File(f), save=True)
        
    print(f"Created movie {movie.name}")
    
    cities = ['Hyderabad', 'Mumbai', 'Bengaluru']
    for city in cities:
        for days_ahead in range(3):
            show_time = timezone.now().replace(hour=18, minute=30, second=0, microsecond=0) + timedelta(days=days_ahead)
            t = Theater.objects.create(
                name=f"PVR Cinemas {city}",
                city=city,
                location=f"Central Mall, {city}",
                ticket_price=250.00,
                movie=movie,
                time=show_time
            )
            seats = []
            for row in ['A', 'B', 'C']:
                for num in range(1, 11):
                    seats.append(Seat(theater=t, seat_number=f"{row}{num}"))
            Seat.objects.bulk_create(seats)
    print(f"Added theaters and seats for {movie.name}")

print('Done seeding real movies!')
