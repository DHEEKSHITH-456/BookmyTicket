# BookMySeat — Online Movie Ticket Booking Platform

**BookMySeat** is a full-stack movie ticket booking web application built using **Python** and **Django** as part of the Full Stack Development Internship. The application provides an end-to-end cinema ticketing experience featuring multi-criteria movie discovery, smart seat reservation with live availability and 2-minute hold timers, secure payment workflows via Razorpay, automated PDF e-ticket generation with scannable QR codes, verified movie reviews, and a real-time admin analytics dashboard.

**Developer / Student:** Dheekshith  
**GitHub Repository:** [https://github.com/DHEEKSHITH-456/BookmyTicket](https://github.com/DHEEKSHITH-456/BookmyTicket)

---

## 🔑 Administrative & Evaluator Credentials

As required by the project guidelines for evaluation, pre-configured test accounts are provided below:

| Role | Username | Password | Email | Access Permissions |
|---|---|---|---|---|
| **Superuser / Head Admin** | `admin` | `admin123` | `admin@example.com` | Full Superuser & Staff Access (Django Admin + Real-Time Dashboard) |
| **Standard Test Patron** | `testuser` | `testpass123` | `test@example.com` | Standard Patron (Booking, Matrix, Reviews, Ledger) |

---

## 🌟 Six Core Tasks & Features

### 🔍 Task 1: Advanced Movie Discovery, Search & Recommendations
- **Full-Text Search**: Case-insensitive search on movie titles, casts, genres, and descriptions.
- **Multi-Faceted Filtering**: Filter movies across 8 distinct criteria:
  - **Genre**: Action, Sci-Fi, Drama, Comedy, Horror, Animation, Adventure, Thriller
  - **Language**: English, Hindi, Telugu, Tamil, etc.
  - **City & Region**: Multi-city cinema filtering (Hyderabad, Mumbai, Bengaluru, Delhi)
  - **Theater Chains**: AMB Cinemas, PVR, INOX, Prasads Multiplex, Cinepolis
  - **Ratings**: 7.0+, 8.0+, 8.5+ threshold filters
  - **Show Timings**: Morning, Afternoon, Evening, Night
  - **Release Status**: Now Showing vs. Upcoming releases
  - **Budget / Ticket Price**: Under ₹200, ₹250, ₹350, ₹500
- **Multi-Criteria Sorting**: By Popularity, Highest Rated, Newest Releases, Price (Low to High & High to Low).
- **Dynamic Counters & Pagination**: Live matching movie counts and query-preserving pagination.
- **Personalized "Recommended for You" Engine**: Triple-tier recommendation strategy based on user booking history, recently viewed movies in session, and trending blockbusters.

### 📄 Task 2: Automated Ticket Generation & Async Email Delivery
- **Automated PDF E-Ticket Generation**: Clean A4 e-tickets generated via **ReportLab** with cinema branding, showtime details, seat assignments, and pricing breakdowns.
- **Scannable QR Codes**: High-contrast gate verification code formatted as `BOOKMYSEAT|<UUID>|<OrderRef>|<Movie>|<Seats>`.
- **Asynchronous Email Processing**: Non-blocking **Celery** background worker with exponential backoff retry policies (`max_retries >= 3`).
- **Post-Booking Confirmation & On-Demand Download**: Dedicated confirmation screen and persistent `/movies/booking/<uuid>/download-ticket/` endpoint in user profile.

### 🎥 Task 3: Movie Management with Trailers, Reviews & Ratings
- **Normalized Relational Schema**: Dedicated models for `Genre`, `Language`, `CastMember`, and gallery still uploads (`MovieImage`).
- **Django Admin Management**: Full CRUD interface for all models with `MovieImageInline` for inline poster and still gallery uploads.
- **Media Embedding**: Responsive YouTube trailers, age certification badges (U, U/A, A, S), and movie metadata.
- **Verified Viewer Reviews**: Reviews and 1–10 star ratings restricted strictly to patrons with confirmed past showtime bookings.
- **Dynamic Average Rating Recalculation**: Automated re-aggregation of movie ratings upon review submission, edit, or deletion.
- **Review Moderation**: Community reporting flag (`is_reported`) and in-place review editing.
- **Content-Based Recommendations**: *"You Might Also Like"* recommendation grid on movie detail pages.

### 💳 Task 4: Complete Payment Workflow & Booking Management
- **Razorpay Integration**: INR currency checkout order creation with temporary seat reservation.
- **Server-Side HMAC-SHA256 Verification**: Cryptographic signature validation strictly rejects tampered requests.
- **Webhook Verifier**: `@csrf_exempt` endpoint verifying `X-Razorpay-Signature` for asynchronous payment capture notifications.
- **Atomic Confirmation**: Database transactions with `select_for_update()` confirm bookings only after successful payment verification.
- **Automatic Seat Release**: Automatic seat release on payment failure, bank decline, user cancellation, or session timeout.
- **Duplicate Prevention (Idempotency)**: Retried callbacks and duplicate webhooks never create duplicate bookings or double-charges.
- **User Profile & History**: Tabbed profile interface showing confirmed bookings alongside a complete payment transaction history.

### 🪑 Task 5: Smart Seat Reservation with Live Availability
- **Interactive Visual Seat Matrix**: Categorized grid with clear status indicators:
  - 🟢 **Available**: Ready for selection.
  - 🟡 **Reserved**: Temporarily held by another user with live countdown timer.
  - 🔴 **Booked**: Confirmed and permanently locked.
  - 🔵 **Your Selection**: Real-time counter and total price calculation.
- **2-Minute Temporary Reservation Engine**: Selected seats remain reserved for precisely 120 seconds (`reserved_until`), after which they are automatically released if payment is abandoned.
- **Modify Selection Pre-Payment**: Users can release held seats and select new seats before proceeding to payment.
- **Concurrency & Race Condition Prevention**: Database transactions with `select_for_update()` ensure atomic seat reservation; multiple simultaneous booking attempts never result in duplicate reservations.
- **Live Availability Polling API**: `/movies/theater/<id>/seats/live/` powers real-time UI synchronization without requiring page refreshes.

### 📊 Task 6: Comprehensive Admin Dashboard & Business Insights
- **Role-Based Security**: Protected by `@user_passes_test(is_admin_user)` restricting access to authenticated users where `is_staff=True` or `is_superuser=True`.
- **Key Revenue & Booking Metrics**: Total gross revenue (daily, weekly, monthly, yearly, custom range), booking volume, Average Ticket Value (ATV), and cancellation and refund statistics.
- **Interactive Chart.js Visualizations**: Dual-axis daily trend line chart, order health donut chart, 24-hour peak hours distribution (`ExtractHour`), and user acquisition growth curves.
- **Occupancy & Leaderboards**: Per-theater occupancy percentages (`booked_seats / total_seats * 100`), top-performing theaters, and most-booked movies.
- **Date Presets & Custom Date Picker**: Quick filters (`Today`, `7 Days`, `30 Days`, `This Month`, `This Year`, `All Time`) + custom date ranges.
- **CSV Export Engine**: Instant downloadable spreadsheets for `revenue`, `bookings`, `theaters`, and `cancellations`.
- **Database Indexing & Query Optimization (100k+ records)**: Composite B-Tree indexes added in migration `0008`. ORM aggregations execute in **sub-5 ms** with zero Python-side record loading, performing efficiently with 100,000+ bookings.

---

## 🛠️ Technology Stack

- **Backend Framework**: Python 3.13, Django 6.0 / 5.1
- **Database & Indexing**: SQLite3 with composite B-Tree indexes (`booked_at`, `theater_date`, `status_created`)
- **PDF & QR Code Engine**: ReportLab, QRCode
- **Asynchronous Task Queue**: Celery, Redis
- **Frontend & Visualizations**: HTML5, CSS3, JavaScript, Bootstrap 4, FontAwesome, Chart.js
- **Static Assets & Deployment**: WhiteNoise, Gunicorn

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Virtual environment (`venv`)

### Installation & Local Setup

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

# 5. Start the local development server
python manage.py runserver 127.0.0.1:8000
```

Open your browser and navigate to:
- **Main Portal**: `http://127.0.0.1:8000/`
- **Admin Dashboard**: `http://127.0.0.1:8000/dashboard/`
- **Django Admin**: `http://127.0.0.1:8000/admin/`

---

## 🧪 Running Verification Test Suites

Comprehensive automated test suites covering all 6 tasks are included under `tests/`:

```bash
# Run unified 6-task master verification test
python tests/master_verification_all_6_tasks.py

# Run Task 1 Movie Discovery & Recommendations test
python tests/test_task1_movie_discovery.py

# Run Task 2 Automated Ticket Generation & Celery Email test
python tests/test_task2_ticket_generation.py

# Run Task 3 Movie Management, Trailers & Reviews test
python tests/test_task3_movie_management.py

# Run comprehensive end-to-end user feature test
python tests/test_all_features_e2e.py

# Run Task 4 Payment Workflow verification
python tests/test_task4_payment.py

# Run Task 5 Smart Seat Reservation & Concurrency test
python tests/test_task5_smart_reservation_comprehensive.py

# Run Task 6 Admin Dashboard, Indexing & Benchmark test
python tests/test_task6_admin_dashboard.py
```

---

## 📄 Documentation

For full architecture diagrams, database schema designs, performance benchmarks, and detailed technical specifications, refer to [project_report.md](project_report.md).

---

## 📄 License

This project is licensed under the MIT License.
