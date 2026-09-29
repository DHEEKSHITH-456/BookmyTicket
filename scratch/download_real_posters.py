import os
import sys
import re
import urllib.request
import django

sys.path.insert(0, r'd:\Intership project\django-bookmyshow-clone')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from movies.models import Movie, Genre, Language
from django.conf import settings

media_movies_dir = os.path.join(settings.MEDIA_ROOT, 'movies')
os.makedirs(media_movies_dir, exist_ok=True)

# TMDb IDs for accurate poster images
movie_configs = {
    'Kalki 2898 AD': {'tmdb_id': 823464, 'filename': 'kalki_2898_ad.jpg'},
    'Deadpool & Wolverine': {'tmdb_id': 533535, 'filename': 'deadpool_and_wolverine.jpg'},
    'Oppenheimer': {'tmdb_id': 872585, 'filename': 'oppenheimer.jpg'},
    'Dune: Part Two': {'tmdb_id': 693134, 'filename': 'dune_part_two.jpg'},
    'RRR': {'tmdb_id': 579974, 'filename': 'rrr.jpg'},
    'Salaar: Part 1  Ceasefire': {'tmdb_id': 848685, 'filename': 'salaar.jpg'},
    'Salaar: Part 1 - Ceasefire': {'tmdb_id': 848685, 'filename': 'salaar.jpg'},
    'Stree 2: Sarkate Ka Aatank': {'tmdb_id': 1139829, 'filename': 'stree_2.jpg'},
    'Jawan': {'tmdb_id': 872906, 'filename': 'jawan.jpg'},
    'Animal': {'tmdb_id': 781732, 'filename': 'animal.jpg'},
    'Leo': {'tmdb_id': 998846, 'filename': 'leo.jpg'},
    'Spider-Man: Across the Spider-Verse': {'tmdb_id': 569094, 'filename': 'spiderman_spiderverse.jpg'},
    'Avengers: Endgame': {'tmdb_id': 299534, 'filename': 'avengers_endgame.jpg'},
    'The Avengers': {'tmdb_id': 24428, 'filename': 'the_avengers.jpg'},
    'Avatar: The Way of Water': {'tmdb_id': 76600, 'filename': 'avatar_way_of_water.jpg'},
    'Avatar': {'tmdb_id': 19995, 'filename': 'avatar.jpg'},
    'The Dark Knight': {'tmdb_id': 155, 'filename': 'the_dark_knight.jpg'},
    'Inception': {'tmdb_id': 27205, 'filename': 'inception.jpg'},
    'Interstellar': {'tmdb_id': 157336, 'filename': 'interstellar.jpg'},
    'Gladiator II': {'tmdb_id': 558449, 'filename': 'gladiator_2.jpg'},
    'Wicked': {'tmdb_id': 402431, 'filename': 'wicked.jpg'},
    'Pushpa 2: The Rule': {'tmdb_id': 927342, 'filename': 'pushpa_2.jpg'},
}

# Update placeholder names in database first
replacements = {
    1: {'name': 'The Avengers', 'genre': 'Action', 'lang': 'English', 'rating': 8.0},
    2: {'name': 'Gladiator II', 'genre': 'Action, Adventure, Drama', 'lang': 'English', 'rating': 8.2},
    3: {'name': 'Wicked', 'genre': 'Fantasy, Musical, Romance', 'lang': 'English', 'rating': 8.3},
    4: {'name': 'Pushpa 2: The Rule', 'genre': 'Action, Crime, Drama', 'lang': 'Telugu', 'rating': 8.9},
    5: {'name': 'Fighter', 'genre': 'Action, Thriller', 'lang': 'Hindi', 'rating': 7.6, 'tmdb_id': 1022789, 'filename': 'fighter.jpg'},
}

for mid, info in replacements.items():
    try:
        m = Movie.objects.get(id=mid)
        m.name = info['name']
        m.rating = info['rating']
        m.save()
        print(f"Renamed Movie #{mid} to '{m.name}'")
    except Movie.DoesNotExist:
        pass

# Also fix Salaar name if it has encoding question mark
for s in Movie.objects.filter(name__icontains='Salaar'):
    s.name = 'Salaar: Part 1 - Ceasefire'
    s.save()

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def get_poster_url(tmdb_id):
    url = f'https://www.themoviedb.org/movie/{tmdb_id}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
            match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            if match:
                img_url = match.group(1).replace('media.themoviedb.org', 'image.tmdb.org')
                return img_url
    except Exception as e:
        print(f"Error fetching tmdb {tmdb_id}: {e}")
    return None

# Process each movie in DB
for movie in Movie.objects.all():
    name = movie.name.strip()
    config = movie_configs.get(name)
    if not config:
        for k, v in movie_configs.items():
            if k.lower() in name.lower() or name.lower() in k.lower():
                config = v
                break
    
    if not config and name == 'Fighter':
        config = {'tmdb_id': 1022789, 'filename': 'fighter.jpg'}

    if config:
        target_path = os.path.join(media_movies_dir, config['filename'])
        rel_path = f"movies/{config['filename']}"
        
        # Download if doesn't exist or is tiny (<5kb)
        if not os.path.exists(target_path) or os.path.getsize(target_path) < 5000:
            poster_url = get_poster_url(config['tmdb_id'])
            if poster_url:
                print(f"Downloading poster for {name} from {poster_url}...")
                try:
                    img_req = urllib.request.Request(poster_url, headers=headers)
                    with urllib.request.urlopen(img_req, timeout=12) as img_resp:
                        content = img_resp.read()
                        with open(target_path, 'wb') as f:
                            f.write(content)
                        print(f"  -> Saved {len(content)} bytes to {config['filename']}")
                except Exception as ex:
                    print(f"  -> Download failed: {ex}")
            else:
                print(f"No poster URL found for {name}")
        else:
            print(f"Poster already cached for {name} ({config['filename']})")
        
        if os.path.exists(target_path):
            movie.image = rel_path
            movie.save()
            print(f"Updated Movie '{movie.name}' image -> {rel_path}")
    else:
        print(f"No config mapped for movie: '{name}'")

print("\nAll movie posters checked and updated!")
