"""
Rich Dataset Seeding Script for BookMySeat.
Populates Movies with genres, languages, release dates, ratings,
Theaters with cities, locations, ticket prices, varied show timings,
and full seat matrices.
"""

import os
import django
from datetime import datetime, date, time, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from movies.models import Movie, Theater, Seat
from django.utils import timezone

def seed_data():
    print("Starting dataset population...")

    # Available poster images in media/movies
    images = [
        'movies/635217f73e372771013edb4c-the-avengers-poster-marvel-movie-canvas1.jpg',
        'movies/download.jpeg',
        'movies/f5VK0h2bprRhR6iRrixcuEfRxSUF4l14F66vQYrsJGmKZ5nTA1.jpg',
        'movies/feUv2SYumXlT8E2RhzlYbZxfEGLG5AVrCPxP1gmAaCusxyPnA1.jpg',
        'movies/IQsBhg9t747dLhjXfsChIGZy4XfugER8BF0Gw5MDhIcnY5nTA1.jpg'
    ]

    movies_data = [
        {
            "name": "Kalki 2898 AD",
            "genre": "Sci-Fi, Action",
            "language": "Telugu",
            "rating": 8.6,
            "duration": 181,
            "popularity": 980,
            "release_date": date(2024, 6, 27),
            "cast": "Prabhas, Amitabh Bachchan, Kamal Haasan, Deepika Padukone",
            "description": "A modern avatar of Vishnu descends to Earth to protect the world from evil forces in a post-apocalyptic future.",
        },
        {
            "name": "Interstellar",
            "genre": "Sci-Fi, Adventure, Drama",
            "language": "English",
            "rating": 8.9,
            "duration": 169,
            "popularity": 1250,
            "release_date": date(2024, 11, 7),
            "cast": "Matthew McConaughey, Anne Hathaway, Jessica Chastain",
            "description": "When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot is tasked with piloting a spacecraft to find a new home.",
        },
        {
            "name": "Inception",
            "genre": "Sci-Fi, Action, Thriller",
            "language": "English",
            "rating": 8.8,
            "duration": 148,
            "popularity": 1100,
            "release_date": date(2023, 7, 16),
            "cast": "Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page",
            "description": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
        },
        {
            "name": "The Dark Knight",
            "genre": "Action, Crime, Drama",
            "language": "English",
            "rating": 9.0,
            "duration": 152,
            "popularity": 1400,
            "release_date": date(2024, 7, 18),
            "cast": "Christian Bale, Heath Ledger, Aaron Eckhart, Gary Oldman",
            "description": "When the menace known as the Joker wreaks havoc on Gotham City, Batman must accept one of the greatest psychological tests of his ability to fight injustice.",
        },
        {
            "name": "Salaar: Part 1 – Ceasefire",
            "genre": "Action, Drama, Thriller",
            "language": "Telugu",
            "rating": 7.9,
            "duration": 175,
            "popularity": 890,
            "release_date": date(2023, 12, 22),
            "cast": "Prabhas, Prithviraj Sukumaran, Shruti Haasan",
            "description": "A gang leader makes a promise to a dying friend and takes on other criminal gangs in the dystopian city of Khansaar.",
        },
        {
            "name": "RRR",
            "genre": "Action, Drama, Historical",
            "language": "Telugu",
            "rating": 8.8,
            "duration": 187,
            "popularity": 1300,
            "release_date": date(2022, 3, 25),
            "cast": "N.T. Rama Rao Jr., Ram Charan, Alia Bhatt, Ajay Devgn",
            "description": "A fearless revolutionary and an officer in the British force come together to fight the colonial oppression.",
        },
        {
            "name": "Oppenheimer",
            "genre": "Biography, Drama, History",
            "language": "English",
            "rating": 8.9,
            "duration": 180,
            "popularity": 1150,
            "release_date": date(2023, 7, 21),
            "cast": "Cillian Murphy, Emily Blunt, Matt Damon, Robert Downey Jr.",
            "description": "The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb during World War II.",
        },
        {
            "name": "Stree 2: Sarkate Ka Aatank",
            "genre": "Comedy, Horror",
            "language": "Hindi",
            "rating": 8.1,
            "duration": 149,
            "popularity": 920,
            "release_date": date(2024, 8, 15),
            "cast": "Rajkummar Rao, Shraddha Kapoor, Pankaj Tripathi",
            "description": "After the events of Stree, the town of Chanderi is being haunted again by a headless entity abducting women.",
        },
        {
            "name": "Deadpool & Wolverine",
            "genre": "Action, Comedy, Sci-Fi",
            "language": "English",
            "rating": 8.0,
            "duration": 128,
            "popularity": 1050,
            "release_date": date(2024, 7, 26),
            "cast": "Ryan Reynolds, Hugh Jackman, Emma Corrin",
            "description": "Wolverine is recovering when he crosses paths with the loudmouth Deadpool. They team up to defeat a common enemy.",
        },
        {
            "name": "Jawan",
            "genre": "Action, Thriller",
            "language": "Hindi",
            "rating": 8.0,
            "duration": 169,
            "popularity": 940,
            "release_date": date(2023, 9, 7),
            "cast": "Shah Rukh Khan, Nayanthara, Vijay Sethupathi",
            "description": "A high-octane action thriller outlining the emotional journey of a man set out to correct the wrongs in society.",
        },
        {
            "name": "Dune: Part Two",
            "genre": "Sci-Fi, Adventure, Action",
            "language": "English",
            "rating": 8.6,
            "duration": 166,
            "popularity": 990,
            "release_date": date(2024, 3, 1),
            "cast": "Timothée Chalamet, Zendaya, Rebecca Ferguson, Javier Bardem",
            "description": "Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.",
        },
        {
            "name": "Animal",
            "genre": "Action, Crime, Drama",
            "language": "Hindi",
            "rating": 7.4,
            "duration": 201,
            "popularity": 870,
            "release_date": date(2023, 12, 1),
            "cast": "Ranbir Kapoor, Anil Kapoor, Bobby Deol, Rashmika Mandanna",
            "description": "A son undergoes a transformation as his bond with his father becomes toxic and dangerous.",
        },
        {
            "name": "Spider-Man: Across the Spider-Verse",
            "genre": "Animation, Action, Adventure",
            "language": "English",
            "rating": 8.7,
            "duration": 140,
            "popularity": 1120,
            "release_date": date(2023, 6, 2),
            "cast": "Shameik Moore, Hailee Steinfeld, Oscar Isaac",
            "description": "Miles Morales catapults across the Multiverse, where he encounters a team of Spider-People charged with protecting its very existence.",
        },
        {
            "name": "Leo",
            "genre": "Action, Crime, Thriller",
            "language": "Tamil",
            "rating": 7.8,
            "duration": 164,
            "popularity": 850,
            "release_date": date(2023, 10, 19),
            "cast": "Vijay, Sanjay Dutt, Trisha Krishnan, Arjun Sarja",
            "description": "A mild-mannered café owner becomes a local hero, triggering consequences with an old gang who suspect his true identity.",
        },
        {
            "name": "Avengers: Endgame",
            "genre": "Action, Adventure, Sci-Fi",
            "language": "English",
            "rating": 8.4,
            "duration": 181,
            "popularity": 1350,
            "release_date": date(2024, 4, 26),
            "cast": "Robert Downey Jr., Chris Evans, Mark Ruffalo, Chris Hemsworth",
            "description": "After the devastating events of Infinity War, the universe is in ruins. With the help of allies, the Avengers assemble once more.",
        },
        {
            "name": "The Avengers",
            "genre": "Action, Sci-Fi",
            "language": "English",
            "rating": 8.0,
            "duration": 143,
            "popularity": 1020,
            "release_date": date(2023, 5, 4),
            "cast": "Robert Downey Jr., Chris Evans, Scarlett Johansson",
            "description": "Earth's mightiest heroes must come together and learn to fight as a team if they are going to stop Loki from enslaving humanity.",
        },
        {
            "name": "Avatar: The Way of Water",
            "genre": "Sci-Fi, Adventure, Action",
            "language": "English",
            "rating": 7.6,
            "duration": 192,
            "popularity": 880,
            "release_date": date(2024, 12, 16),
            "cast": "Sam Worthington, Zoe Saldana, Sigourney Weaver",
            "description": "Jake Sully lives with his newfound family on Pandora. Once a familiar threat returns, Jake must work with the Na'vi to protect their planet.",
        }
    ]

    city_theaters = {
        "Hyderabad": [
            {"name": "AMB Cinemas: Gachibowli", "location": "Sarath City Capital Mall, Gachibowli"},
            {"name": "Prasads Multiplex: Necklace Road", "location": "NTR Gardens, Khairatabad"},
            {"name": "PVR: Forum Mall Kukatpally", "location": "Nexus Hyderabad, KPHB"},
            {"name": "INOX: GVK One Mall", "location": "Banjara Hills Road No 1"},
            {"name": "Cinepolis: DSL Virtue Mall", "location": "Uppal, Hyderabad"}
        ],
        "Mumbai": [
            {"name": "PVR ICON: Phoenix Palladium", "location": "Lower Parel, Mumbai"},
            {"name": "INOX: Insignia at R City", "location": "Ghatkopar West, Mumbai"},
            {"name": "Cinepolis: Viviana Mall", "location": "Thane West, Mumbai"},
            {"name": "PVR: Juhu PXL", "location": "Dynamix Mall, Juhu, Mumbai"}
        ],
        "Bengaluru": [
            {"name": "PVR: Orion Mall Rajajinagar", "location": "Brigade Gateway, Bengaluru"},
            {"name": "INOX: Nexus Koramangala", "location": "Koramangala, Bengaluru"},
            {"name": "Cinepolis: Royal Meenakshi Mall", "location": "Bannerghatta Main Rd, Bengaluru"},
            {"name": "PVR IMAX: Vega City Mall", "location": "BTM Layout, Bengaluru"}
        ],
        "Delhi": [
            {"name": "PVR: Vegas Mall Dwarka", "location": "Sector 14 Dwarka, Delhi"},
            {"name": "INOX: Pacific Mall Tagore Garden", "location": "Tagore Garden, New Delhi"},
            {"name": "PVR: Select Citywalk Saket", "location": "Saket District Centre, New Delhi"},
            {"name": "Cinepolis: DLF Avenue Saket", "location": "Saket, New Delhi"}
        ]
    }

    # Show times by slot
    show_slots = [
        ("Morning", time(9, 30), 180.00),
        ("Morning", time(11, 0), 200.00),
        ("Afternoon", time(13, 30), 220.00),
        ("Afternoon", time(16, 0), 250.00),
        ("Evening", time(18, 30), 300.00),
        ("Evening", time(20, 0), 350.00),
        ("Night", time(22, 30), 280.00),
    ]

    base_date = timezone.now().date()

    created_movies = []
    for i, m_info in enumerate(movies_data):
        movie, created = Movie.objects.get_or_create(
            name=m_info["name"],
            defaults={
                "genre": m_info["genre"],
                "language": m_info["language"],
                "rating": m_info["rating"],
                "duration": m_info["duration"],
                "popularity": m_info["popularity"],
                "release_date": m_info["release_date"],
                "cast": m_info["cast"],
                "description": m_info["description"],
                "image": images[i % len(images)]
            }
        )
        if not created:
            movie.genre = m_info["genre"]
            movie.language = m_info["language"]
            movie.rating = m_info["rating"]
            movie.duration = m_info["duration"]
            movie.popularity = m_info["popularity"]
            movie.release_date = m_info["release_date"]
            movie.cast = m_info["cast"]
            movie.description = m_info["description"]
            if not movie.image:
                movie.image = images[i % len(images)]
            movie.save()
        created_movies.append(movie)

    print(f"Created/Updated {len(created_movies)} Movies.")

    # Create Theaters and Seats
    theater_count = 0
    seat_count = 0

    for movie in created_movies:
        # Schedule showtimes across cities for today and tomorrow
        for day_offset in range(2):
            show_day = base_date + timedelta(days=day_offset)
            for city, theaters in city_theaters.items():
                for t_info in theaters[:2]: # 2 theaters per city per movie
                    for slot_name, slot_time, price in show_slots[::2]: # 4 slots
                        show_datetime = timezone.make_aware(
                            datetime.combine(show_day, slot_time)
                        )
                        theater, t_created = Theater.objects.get_or_create(
                            name=t_info["name"],
                            city=city,
                            movie=movie,
                            time=show_datetime,
                            defaults={
                                "location": t_info["location"],
                                "ticket_price": price,
                            }
                        )
                        theater_count += 1

                        # Create 30 seats per theater (A1-A10, B1-B10, C1-C10)
                        if theater.seats.count() < 30:
                            for row in ['A', 'B', 'C']:
                                for num in range(1, 11):
                                    seat_num = f"{row}{num}"
                                    is_booked = (num in [2, 5] and row == 'B') # some sample booked seats
                                    Seat.objects.get_or_create(
                                        theater=theater,
                                        seat_number=seat_num,
                                        defaults={"is_booked": is_booked}
                                    )
                                    seat_count += 1

    print(f"Successfully populated {theater_count} Theater showtimes and {seat_count} Seats across 4 cities!")

if __name__ == '__main__':
    seed_data()
