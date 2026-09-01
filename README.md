# 🎬 BookMySeat — Online Movie Ticket Booking Platform

**BookMySeat** is a full-stack cinema ticketing and movie discovery web application built using **Python** and **Django**. It provides an intuitive, feature-rich experience for discovering movies, exploring showtimes across cinema theaters, selecting seats interactively, and booking tickets with automated e-ticket confirmations.

---

## 🌟 Key Features

### 🔍 1. Advanced Movie Discovery & Search
- **Full-Text Search**: Search movies by title, cast, genre, and description.
- **Multi-Faceted Filtering**: Filter movies by:
  - **Genre**: Action, Sci-Fi, Drama, Comedy, Horror, Animation, Adventure, Thriller
  - **Language**: English, Hindi, Telugu, Tamil, etc.
  - **City & Region**: Multi-city cinema filtering (Hyderabad, Mumbai, Bengaluru, Delhi)
  - **Theater Chains**: AMB Cinemas, PVR, INOX, Prasads Multiplex, Cinepolis
  - **Ratings**: 7.0+, 8.0+, 8.5+ threshold filters
  - **Show Timings**: Morning, Afternoon, Evening, Night
  - **Release Status**: Now Showing vs. Upcoming releases
  - **Budget / Ticket Price**: Under ₹200, ₹250, ₹350, ₹500
- **Multi-Criteria Sorting**: By Popularity, Highest Rated, Newest Releases, Price (Low to High & High to Low).
- **Dynamic Counters & Pagination**: Live matching movie counts and 6-movie page splits.

### ✨ 2. Personalized "Recommended for You" Engine
- **Booking History Strategy**: Recommends movies matching genres and languages of user's past bookings.
- **Recently Viewed Strategy**: Uses session storage to suggest similar films.
- **Trending Fallback**: Displays top-rated blockbusters for new visitors.

### 🎟️ 3. Interactive Seat Selection & Booking
- Real-time seat matrix with available, selected, and sold indicators.
- Live price and seat count calculation.
- Concurrency-safe atomic database transactions (`select_for_update`) to prevent double-booking.

### 📄 4. Automated Ticket Generation & Verification
- Professional cinema-style PDF e-tickets generated with **ReportLab**.
- Embedded high-contrast **QR Code** for ticket gate verification.
- On-demand PDF ticket downloading from user booking history.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.13, Django 6.0 / 5.1
- **Database**: SQLite3
- **PDF & QR Engine**: ReportLab, QRCode
- **Async Processing**: Celery, Redis
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 4, FontAwesome
- **Static Assets**: WhiteNoise

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Virtual environment (`venv`)

### Installation & Setup

```bash
# 1. Clone the repository
git clone https://github.com/DHEEKSHITH-456/BookmyTicket.git
cd BookmyTicket

# 2. Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 3. Install required packages
pip install -r requirements.txt

# 4. Apply database migrations
python manage.py migrate

# 5. Populate seed dataset (optional)
python seed_discovery_data.py

# 6. Start the local development server
python manage.py runserver 127.0.0.1:8000
```

Open your browser and navigate to `http://127.0.0.1:8000/`.

---

## 📄 License

This project is licensed under the MIT License.
