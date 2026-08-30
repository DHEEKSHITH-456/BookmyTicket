import os
import django
import urllib.request

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyticket.settings')
django.setup()

from movies.models import Movie, Theater, Seat
from django.core.files import File
from datetime import date, time
import random

# List of movies with details and reliable poster URLs
movies_data = [
    {
        "name": "Dune: Part Two",
        "rating": 8.6,
        "genre": "Sci-Fi / Adventure",
        "cast": "Timothée Chalamet, Zendaya, Rebecca Ferguson, Austin Butler",
        "description": "Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.",
        "release_date": date(2024, 3, 1),
        "duration": 166,
        "poster_url": "https://m.media-amazon.com/images/M/MV5BN2QyZGU4ZDctOWMzMy00NTc5LThlOGQtODhmNDI1NmY5YzAwXkEyXkFqcGc@._V1_FMjpg_UX1000_.jpg",
        "filename": "dune2.jpg"
    },
    {
        "name": "Oppenheimer",
        "rating": 8.9,
        "genre": "Drama / Biography",
        "cast": "Cillian Murphy, Emily Blunt, Matt Damon, Robert Downey Jr.",
        "description": "The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb.",
        "release_date": date(2023, 7, 21),
        "duration": 180,
        "poster_url": "https://m.media-amazon.com/images/M/MV5BN2JkMDc5MGQtZjg3YS00NmFiLWIyZmQtZTJmNTM5MjVmYTQ4XkEyXkFqcGc@._V1_FMjpg_UX1000_.jpg",
        "filename": "oppenheimer.jpg"
    },
    {
        "name": "Interstellar",
        "rating": 8.7,
        "genre": "Sci-Fi / Drama",
        "cast": "Matthew McConaughey, Anne Hathaway, Jessica Chastain, Michael Caine",
        "description": "When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot, Joseph Cooper, is tasked to pilot a spacecraft along with a team of researchers to find a new planet for humans.",
        "release_date": date(2014, 11, 7),
        "duration": 169,
        "poster_url": "https://m.media-amazon.com/images/M/MV5BYzdjMDAxZGItMjI2My00ODA1LTlkNzItOWFjMDU5ZDJlYWY3XkEyXkFqcGc@._V1_FMjpg_UX1000_.jpg",
        "filename": "interstellar.jpg"
    },
    {
        "name": "The Dark Knight",
        "rating": 9.0,
        "genre": "Action / Crime / Drama",
        "cast": "Christian Bale, Heath Ledger, Aaron Eckhart, Michael Caine",
        "description": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
        "release_date": date(2008, 7, 18),
        "duration": 152,
        "poster_url": "https://m.media-amazon.com/images/M/MV5BMTMxNTMwODM0NF5BMl5BanBnXkFtZTcwODAyMTk2Mw@@._V1_FMjpg_UX1000_.jpg",
        "filename": "dark_knight.jpg"
    },
    {
        "name": "Inception",
        "rating": 8.8,
        "genre": "Action / Sci-Fi / Thriller",
        "cast": "Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page, Tom Hardy",
        "description": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
        "release_date": date(2010, 7, 16),
        "duration": 148,
        "poster_url": "https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@._V1_FMjpg_UX1000_.jpg",
        "filename": "inception.jpg"
    },
    {
        "name": "Kalki 2898 AD",
        "rating": 7.6,
        "genre": "Action / Sci-Fi",
        "cast": "Prabhas, Amitabh Bachchan, Kamal Haasan, Deepika Padukone",
        "description": "A modern-day avatar of Vishnu, a Hindu god, who is believed to have descended to the earth to protect the world from evil forces.",
        "release_date": date(2024, 6, 27),
        "duration": 181,
        "poster_url": "https://m.media-amazon.com/images/M/MV5BMTcxNjg4ZjYtYTI3OS00MDZiLWE1MzItNmY2NTQ4NDY2ODliXkEyXkFqcGc@._V1_FMjpg_UX1000_.jpg",
        "filename": "kalki.jpg"
    },
    {
        "name": "Deadpool & Wolverine",
        "rating": 7.7,
        "genre": "Action / Comedy / Sci-Fi",
        "cast": "Ryan Reynolds, Hugh Jackman, Emma Corrin, Matthew Macfadyen",
        "description": "Deadpool is offered a place in the Marvel Cinematic Universe by the Time Variance Authority, but instead recruits a variant of Wolverine to save his universe from extinction.",
        "release_date": date(2024, 7, 26),
        "duration": 128,
        "poster_url": "https://m.media-amazon.com/images/M/MV5BNzRiMjg0MzUtNTQ1Eg@@._V1_FMjpg_UX1000_.jpg",
        "filename": "deadpool_wolverine.jpg"
    },
    {
        "name": "Spider-Man: Across the Spider-Verse",
        "rating": 8.6,
        "genre": "Animation / Action / Adventure",
        "cast": "Shameik Moore, Hailee Steinfeld, Oscar Isaac, Jake Johnson",
        "description": "Miles Morales catapults across the Multiverse, where he encounters a team of Spider-People charged with protecting its very existence.",
        "release_date": date(2023, 6, 2),
        "duration": 140,
        "poster_url": "https://m.media-amazon.com/images/M/MV5BMzI0NmVkMjEtYmY4MS00ZDMxLTlkZmEtMzU4MDQxYTMzMjU2XkEyXkFqcGc@._V1_FMjpg_UX1000_.jpg",
        "filename": "spider_verse.jpg"
    }
]

theaters_template = [
    {"name": "PVR: Forum Mall, Kukatpally", "location": "Forum Sujana Mall, Hyderabad", "time": time(10, 30), "capacity": 50},
    {"name": "INOX: GVK One, Banjara Hills", "location": "GVK One Mall, Road No. 1, Hyderabad", "time": time(14, 15), "capacity": 50},
    {"name": "AMB Cinemas: Gachibowli", "location": "Sarath City Capital Mall, Hyderabad", "time": time(18, 45), "capacity": 50},
    {"name": "Cinepolis: CCPL Mall, Malkajgiri", "location": "CCPL Mall, Hyderabad", "time": time(21, 30), "capacity": 50},
]

rows = ['A', 'B', 'C', 'D', 'E', 'F']
cols_per_row = 10  # A1 to A10, B1 to B10, etc. (60 seats)

media_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'movie_images')
os.makedirs(media_dir, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for m_data in movies_data:
    # Check if movie already exists
    movie = Movie.objects.filter(name=m_data['name']).first()
    
    # Download image
    local_img_path = os.path.join(media_dir, m_data['filename'])
    if not os.path.exists(local_img_path):
        try:
            req = urllib.request.Request(m_data['poster_url'], headers=headers)
            with urllib.request.urlopen(req) as resp, open(local_img_path, 'wb') as out_f:
                out_f.write(resp.read())
            print(f"Downloaded poster for {m_data['name']}")
        except Exception as e:
            print(f"Could not download poster for {m_data['name']}: {e}")
            # Fallback to avatar poster if exists
            local_img_path = 'movie_images/MV5BMDEzMmQwZjctZWU2My00MWNlLWE0NjItMDJlYTRlNGJiZjcyXkEyXkFqcGc._V1_FMjpg_UX1000_.jpg'

    rel_img_path = f"movie_images/{m_data['filename']}" if os.path.exists(local_img_path) else 'movie_images/MV5BMDEzMmQwZjctZWU2My00MWNlLWE0NjItMDJlYTRlNGJiZjcyXkEyXkFqcGc._V1_FMjpg_UX1000_.jpg'

    if not movie:
        movie = Movie.objects.create(
            name=m_data['name'],
            image=rel_img_path,
            rating=m_data['rating'],
            cast=m_data['cast'],
            description=m_data['description'],
            release_date=m_data['release_date'],
            duration=m_data['duration'],
            genre=m_data['genre']
        )
        print(f"Created movie: {movie.name}")
    else:
        movie.image = rel_img_path
        movie.genre = m_data['genre']
        movie.rating = m_data['rating']
        movie.duration = m_data['duration']
        movie.save()
        print(f"Updated movie: {movie.name}")

    # Add theaters for this movie
    for t_info in theaters_template:
        theater, created = Theater.objects.get_or_create(
            movie=movie,
            name=t_info['name'],
            time=t_info['time'],
            defaults={
                'location': t_info['location'],
                'capacity': 60
            }
        )
        
        # Check seats count
        existing_seats = Seat.objects.filter(theater=theater).count()
        if existing_seats < 60:
            Seat.objects.filter(theater=theater).delete()
            seats_to_create = []
            for r in rows:
                for c in range(1, cols_per_row + 1):
                    seat_num = f"{r}{c}"
                    # Randomly mark 15% of seats as booked for realism
                    is_booked = random.random() < 0.18
                    seats_to_create.append(
                        Seat(theater=theater, seat_number=seat_num, is_booked=is_booked)
                    )
            Seat.objects.bulk_create(seats_to_create)
            print(f"  Created 60 seats for {theater.name}")

# Also ensure Avatar has 60 seats in its theaters if any
avatar = Movie.objects.filter(name__icontains="AVATAR").first()
if avatar:
    for t_info in theaters_template:
        t, _ = Theater.objects.get_or_create(
            movie=avatar,
            name=t_info['name'],
            time=t_info['time'],
            defaults={'location': t_info['location'], 'capacity': 60}
        )
        if Seat.objects.filter(theater=t).count() < 60:
            Seat.objects.filter(theater=t).delete()
            seats_to_create = [
                Seat(theater=t, seat_number=f"{r}{c}", is_booked=(random.random() < 0.2))
                for r in rows for c in range(1, cols_per_row + 1)
            ]
            Seat.objects.bulk_create(seats_to_create)

print("Database population complete!")
