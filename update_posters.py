import os
import django
import urllib.request

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyticket.settings')
django.setup()

from movies.models import Movie

media_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'movie_images')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

posters = {
    "Dune: Part Two": ("https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg", "dune2.jpg"),
    "Kalki 2898 AD": ("https://image.tmdb.org/t/p/w500/3p67UeG8tXo4Rk1uWqgQ9QfUe4.jpg", "kalki.jpg"),
    "Deadpool & Wolverine": ("https://image.tmdb.org/t/p/w500/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg", "deadpool_wolverine.jpg"),
    "Spider-Man: Across the Spider-Verse": ("https://image.tmdb.org/t/p/w500/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg", "spider_verse.jpg"),
}

for name, (url, filename) in posters.items():
    local_path = os.path.join(media_dir, filename)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(local_path, 'wb') as out_f:
            out_f.write(resp.read())
        print(f"Successfully downloaded {filename}")
        
        movie = Movie.objects.filter(name=name).first()
        if movie:
            movie.image = f"movie_images/{filename}"
            movie.save()
            print(f"Updated {name} image field.")
    except Exception as e:
        print(f"Error for {name}: {e}")

print("Posters update complete!")
