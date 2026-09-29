import urllib.request
import re
import os
import sys
import django

sys.path.insert(0, r'd:\Intership project\django-bookmyshow-clone')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from movies.models import Movie
from django.conf import settings

media_dir = os.path.join(settings.MEDIA_ROOT, 'movies')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

pages = [
    ('Kalki 2898 AD', 'https://en.wikipedia.org/wiki/Kalki_2898_AD', 'kalki_2898_ad.jpg'),
    ('Stree 2: Sarkate Ka Aatank', 'https://en.wikipedia.org/wiki/Stree_2', 'stree_2.jpg'),
    ('Jawan', 'https://en.wikipedia.org/wiki/Jawan_(film)', 'jawan.jpg'),
    ('Animal', 'https://en.wikipedia.org/wiki/Animal_(2023_film)', 'animal.jpg'),
    ('Leo', 'https://en.wikipedia.org/wiki/Leo_(2023_Indian_film)', 'leo.jpg'),
    ('Pushpa 2: The Rule', 'https://en.wikipedia.org/wiki/Pushpa_2:_The_Rule', 'pushpa_2.jpg'),
    ('Fighter', 'https://en.wikipedia.org/wiki/Fighter_(2024_film)', 'fighter.jpg')
]

for name, url, filename in pages:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
            match = re.search(r'class="infobox-image"[^>]*>.*?<img[^>]+src="([^"]+)"', html, re.DOTALL)
            if match:
                raw_src = match.group(1)
                img_src = 'https:' + raw_src if raw_src.startswith('//') else raw_src
                print(f"Found infobox for {name}: {img_src}")
                
                # Download
                target_path = os.path.join(media_dir, filename)
                img_req = urllib.request.Request(img_src, headers=headers)
                with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                    data = img_resp.read()
                    if len(data) > 1000:
                        with open(target_path, 'wb') as f:
                            f.write(data)
                        print(f"  [OK] Saved {len(data)} bytes to {filename}")
                        
                        # Assign to movie
                        movies = Movie.objects.filter(name__icontains=name.split(':')[0])
                        for m in movies:
                            m.image = f"movies/{filename}"
                            m.save()
                            print(f"  Updated Movie '{m.name}' -> movies/{filename}")
                    else:
                        print(f"  [WARN] Tiny image: {len(data)} bytes")
            else:
                print(f"No infobox-image found on {url}")
    except Exception as e:
        print(f"Error fetching {name}: {e}")

print("Done processing wikipedia posters!")
