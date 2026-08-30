import os
import urllib.request

static_img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images')
os.makedirs(static_img_dir, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

images = {
    "concerts.jpg": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=600&auto=format&fit=crop&q=80",
    "comedy.jpg": "https://images.unsplash.com/photo-1585699324551-f6c309eedeca?w=600&auto=format&fit=crop&q=80",
    "workshops.jpg": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600&auto=format&fit=crop&q=80",
    "kids.jpg": "https://images.unsplash.com/photo-1566737236500-c8ac43014a67?w=600&auto=format&fit=crop&q=80",
    "sports.jpg": "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&auto=format&fit=crop&q=80",
    "banner1.jpg": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=1600&auto=format&fit=crop&q=80",
    "banner2.jpg": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=1600&auto=format&fit=crop&q=80",
    "banner3.jpg": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=1600&auto=format&fit=crop&q=80",
}

for filename, url in images.items():
    filepath = os.path.join(static_img_dir, filename)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(filepath, 'wb') as out_f:
            out_f.write(resp.read())
        print(f"Downloaded {filename} ({os.path.getsize(filepath)} bytes)")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")

print("Static image downloads complete!")
