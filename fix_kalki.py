import os
import django
import urllib.request

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyticket.settings')
django.setup()

from movies.models import Movie

media_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'movie_images')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Avatar poster URL & RRR / Kalki working poster URL
urls = [
    ("Kalki 2898 AD", "https://upload.wikimedia.org/wikipedia/en/4/4c/Kalki_2898_AD.jpg", "kalki.jpg"),
    ("AVATAR", "https://image.tmdb.org/t/p/w500/kyeqWdyUXW608qlYkRqosgbbJyK.jpg", "avatar.jpg"),
]

for name, url, filename in urls:
    local_path = os.path.join(media_dir, filename)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(local_path, 'wb') as out_f:
            out_f.write(resp.read())
        print(f"Downloaded {filename}")
        
        movie = Movie.objects.filter(name__icontains=name.split()[0]).first()
        if movie:
            movie.image = f"movie_images/{filename}"
            movie.save()
            print(f"Updated {movie.name}")
    except Exception as e:
        print(f"Error {name}: {e}")
