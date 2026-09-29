import csv
import json
from decimal import Decimal
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import (
    Count, Sum, Avg, Q, Value, F, FloatField, ExpressionWrapper
)
from django.db.models.functions import TruncDate, ExtractHour, Coalesce, Cast, NullIf
from django.contrib.auth.models import User

from .models import Movie, Theater, Seat, PaymentTransaction, Booking


def is_admin_user(user):
    """Check if the user has staff or superuser privileges."""
    return user.is_authenticated and (user.is_staff or user.is_superuser) and user.username != 'testuser'


def get_date_range(request):
    """
    Parse date range from GET parameters with preset support.
    Returns (start_dt, end_dt, start_str, end_str, preset_name).
    """
    now = timezone.now()
    today = now.date()
    preset = request.GET.get('preset', '').strip().lower()
    start_str = request.GET.get('start_date', '').strip()
    end_str = request.GET.get('end_date', '').strip()

    if preset == 'today':
        start_date = today
        end_date = today
    elif preset == '7days':
        start_date = today - timedelta(days=7)
        end_date = today
    elif preset == '30days':
        start_date = today - timedelta(days=30)
        end_date = today
    elif preset == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
    elif preset == 'this_year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif preset == 'all_time':
        start_date = today - timedelta(days=365 * 5)
        end_date = today
    elif start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            preset = 'custom'
        except ValueError:
            start_date = today - timedelta(days=30)
            end_date = today
            preset = '30days'
    else:
        # Default: Past 30 Days
        start_date = today - timedelta(days=30)
        end_date = today
        preset = '30days'

    # Ensure start <= end
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    return start_dt, end_dt, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), preset


@login_required(login_url='/login/')
@user_passes_test(is_admin_user, login_url='/login/', redirect_field_name='next')
def admin_dashboard(request):
    """
    High-Performance Admin Business Insights Dashboard.
    All metrics and analytics are computed directly via optimized database aggregations.
    """
    now = timezone.now()
    today = now.date()

    start_dt, end_dt, start_date_str, end_date_str, preset = get_date_range(request)

    # ==========================================================
    #  1. TOTAL REVENUE (Daily, Weekly, Monthly, Yearly, Custom)
    # ==========================================================
    success_txns = PaymentTransaction.objects.filter(status=PaymentTransaction.STATUS_SUCCESS)

    daily_rev = success_txns.filter(created_at__date=today).aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00')))
    )['total']

    weekly_rev = success_txns.filter(created_at__date__gte=today - timedelta(days=7)).aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00')))
    )['total']

    monthly_rev = success_txns.filter(created_at__date__gte=today - timedelta(days=30)).aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00')))
    )['total']

    yearly_rev = success_txns.filter(created_at__year=today.year).aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00')))
    )['total']

    all_time_rev = success_txns.aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00')))
    )['total']

    period_rev = success_txns.filter(created_at__range=(start_dt, end_dt)).aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00')))
    )['total']

    period_bookings_count = Booking.objects.filter(booked_at__range=(start_dt, end_dt)).count()
    all_time_bookings_count = Booking.objects.count()

    # ==========================================================
    #  2. BOOKING & REVENUE TRENDS (Database TruncDate)
    # ==========================================================
    trend_qs = (
        Booking.objects.filter(booked_at__range=(start_dt, end_dt))
        .annotate(date=TruncDate('booked_at'))
        .values('date')
        .annotate(
            bookings_count=Count('id'),
            revenue=Coalesce(Sum('payment__amount', filter=Q(payment__status=PaymentTransaction.STATUS_SUCCESS)), Value(Decimal('0.00')))
        )
        .order_by('date')
    )

    trend_dates = []
    trend_counts = []
    trend_revenues = []
    for item in trend_qs:
        date_label = item['date'].strftime('%b %d') if hasattr(item['date'], 'strftime') else str(item['date'])
        trend_dates.append(date_label)
        trend_counts.append(item['bookings_count'])
        trend_revenues.append(float(item['revenue']))

    # ==========================================================
    #  3. THEATER OCCUPANCY PERCENTAGES (Database Aggregation)
    # ==========================================================
    theaters_qs = (
        Theater.objects.select_related('movie')
        .annotate(
            total_seats_count=Count('seats', distinct=True),
            booked_seats_count=Count('seats', filter=Q(seats__is_booked=True), distinct=True),
            period_tickets=Count('bookings', filter=Q(bookings__booked_at__range=(start_dt, end_dt)), distinct=True),
            period_revenue=Coalesce(
                Sum('bookings__payment__amount', filter=Q(
                    bookings__booked_at__range=(start_dt, end_dt),
                    bookings__payment__status=PaymentTransaction.STATUS_SUCCESS
                )),
                Value(Decimal('0.00'))
            )
        )
    )

    theater_occupancies = []
    total_system_seats = 0
    total_system_booked = 0

    for t in theaters_qs:
        total_seats = t.total_seats_count
        booked_seats = t.booked_seats_count
        occupancy_pct = round((booked_seats / total_seats * 100), 1) if total_seats > 0 else 0.0
        total_system_seats += total_seats
        total_system_booked += booked_seats

        theater_occupancies.append({
            'id': t.id,
            'name': t.name,
            'movie_name': t.movie.name,
            'city': t.city,
            'time': t.time,
            'ticket_price': t.ticket_price,
            'total_seats': total_seats,
            'booked_seats': booked_seats,
            'available_seats': max(0, total_seats - booked_seats),
            'occupancy_pct': occupancy_pct,
            'period_tickets': t.period_tickets,
            'period_revenue': t.period_revenue,
        })

    # Sort theaters by occupancy descending
    theater_occupancies.sort(key=lambda x: x['occupancy_pct'], reverse=True)
    overall_occupancy_pct = round((total_system_booked / total_system_seats * 100), 1) if total_system_seats > 0 else 0.0

    # ==========================================================
    #  4. MOST BOOKED MOVIES
    # ==========================================================
    top_movies = list(
        Movie.objects.annotate(
            period_bookings=Count('bookings', filter=Q(bookings__booked_at__range=(start_dt, end_dt))),
            period_gross=Coalesce(
                Sum('bookings__payment__amount', filter=Q(
                    bookings__booked_at__range=(start_dt, end_dt),
                    bookings__payment__status=PaymentTransaction.STATUS_SUCCESS
                )),
                Value(Decimal('0.00'))
            )
        )
        .filter(period_bookings__gt=0)
        .order_by('-period_bookings', '-period_gross')[:8]
    )

    # If no bookings in narrow custom range, fallback to all-time top movies
    if not top_movies:
        top_movies = list(
            Movie.objects.annotate(
                period_bookings=Count('bookings'),
                period_gross=Coalesce(
                    Sum('bookings__payment__amount', filter=Q(bookings__payment__status=PaymentTransaction.STATUS_SUCCESS)),
                    Value(Decimal('0.00'))
                )
            )
            .order_by('-period_bookings', '-popularity')[:8]
        )

    # ==========================================================
    #  5. TOP-PERFORMING THEATERS
    # ==========================================================
    top_theaters = list(
        Theater.objects.select_related('movie')
        .annotate(
            tickets_sold=Count('bookings', filter=Q(bookings__booked_at__range=(start_dt, end_dt))),
            gross_revenue=Coalesce(
                Sum('bookings__payment__amount', filter=Q(
                    bookings__booked_at__range=(start_dt, end_dt),
                    bookings__payment__status=PaymentTransaction.STATUS_SUCCESS
                )),
                Value(Decimal('0.00'))
            )
        )
        .filter(tickets_sold__gt=0)
        .order_by('-gross_revenue', '-tickets_sold')[:8]
    )

    if not top_theaters:
        top_theaters = list(
            Theater.objects.select_related('movie')
            .annotate(
                tickets_sold=Count('bookings'),
                gross_revenue=Coalesce(
                    Sum('bookings__payment__amount', filter=Q(bookings__payment__status=PaymentTransaction.STATUS_SUCCESS)),
                    Value(Decimal('0.00'))
                )
            )
            .order_by('-gross_revenue')[:8]
        )

    # ==========================================================
    #  6. PEAK BOOKING HOURS (ExtractHour 0-23)
    # ==========================================================
    hourly_qs = (
        Booking.objects.filter(booked_at__range=(start_dt, end_dt))
        .annotate(hour=ExtractHour('booked_at'))
        .values('hour')
        .annotate(bookings=Count('id'))
        .order_by('hour')
    )

    hourly_map = {h: 0 for h in range(24)}
    for row in hourly_qs:
        if row['hour'] is not None:
            hourly_map[int(row['hour'])] = row['bookings']

    peak_hour = max(hourly_map, key=hourly_map.get) if any(hourly_map.values()) else 20
    peak_count = hourly_map[peak_hour]
    peak_label = f"{peak_hour:02d}:00 - {(peak_hour+1)%24:02d}:00"

    hourly_labels = [f"{h:02d}:00" for h in range(24)]
    hourly_counts = [hourly_map[h] for h in range(24)]

    # ==========================================================
    #  7. CANCELLATION AND REFUND STATISTICS
    # ==========================================================
    txn_stats = PaymentTransaction.objects.filter(created_at__range=(start_dt, end_dt)).aggregate(
        total_txns=Count('id'),
        success_count=Count('id', filter=Q(status=PaymentTransaction.STATUS_SUCCESS)),
        success_amount=Coalesce(Sum('amount', filter=Q(status=PaymentTransaction.STATUS_SUCCESS)), Value(Decimal('0.00'))),
        cancelled_count=Count('id', filter=Q(status=PaymentTransaction.STATUS_CANCELLED)),
        cancelled_amount=Coalesce(Sum('amount', filter=Q(status=PaymentTransaction.STATUS_CANCELLED)), Value(Decimal('0.00'))),
        failed_count=Count('id', filter=Q(status=PaymentTransaction.STATUS_FAILED)),
        refunded_count=Count('id', filter=Q(status=PaymentTransaction.STATUS_REFUNDED)),
        refunded_amount=Coalesce(Sum('amount', filter=Q(status=PaymentTransaction.STATUS_REFUNDED)), Value(Decimal('0.00'))),
    )

    total_txns = txn_stats['total_txns'] or 0
    cancelled_count = txn_stats['cancelled_count'] or 0
    refunded_count = txn_stats['refunded_count'] or 0
    success_count = txn_stats['success_count'] or 0
    failed_count = txn_stats['failed_count'] or 0

    cancellation_rate = round((cancelled_count / total_txns * 100), 1) if total_txns > 0 else 0.0
    refund_rate = round((refunded_count / total_txns * 100), 1) if total_txns > 0 else 0.0
    success_rate = round((success_count / total_txns * 100), 1) if total_txns > 0 else 0.0

    # ==========================================================
    #  8. USER GROWTH REPORTS
    # ==========================================================
    total_users_count = User.objects.count()
    new_users_period = User.objects.filter(date_joined__range=(start_dt, end_dt)).count()
    active_booking_users = User.objects.filter(bookings__booked_at__range=(start_dt, end_dt)).distinct().count()

    user_growth_qs = (
        User.objects.filter(date_joined__range=(start_dt, end_dt))
        .annotate(date=TruncDate('date_joined'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    user_growth_dates = [u['date'].strftime('%b %d') if hasattr(u['date'], 'strftime') else str(u['date']) for u in user_growth_qs]
    user_growth_counts = [u['count'] for u in user_growth_qs]

    context = {
        # Active Date Filter
        'start_date': start_date_str,
        'end_date': end_date_str,
        'preset': preset,
        
        # Revenue Insights
        'daily_rev': daily_rev,
        'weekly_rev': weekly_rev,
        'monthly_rev': monthly_rev,
        'yearly_rev': yearly_rev,
        'all_time_rev': all_time_rev,
        'period_rev': period_rev,
        'period_bookings_count': period_bookings_count,
        'all_time_bookings_count': all_time_bookings_count,

        # Trends (for Chart.js)
        'trend_dates_json': json.dumps(trend_dates),
        'trend_counts_json': json.dumps(trend_counts),
        'trend_revenues_json': json.dumps(trend_revenues),

        # Theaters & Occupancy
        'theater_occupancies': theater_occupancies[:20],
        'total_system_seats': total_system_seats,
        'total_system_booked': total_system_booked,
        'overall_occupancy_pct': overall_occupancy_pct,

        # Rankings
        'top_movies': top_movies,
        'top_theaters': top_theaters,

        # Peak Hours
        'peak_label': peak_label,
        'peak_count': peak_count,
        'hourly_labels_json': json.dumps(hourly_labels),
        'hourly_counts_json': json.dumps(hourly_counts),

        # Cancellations & Refunds
        'txn_stats': txn_stats,
        'cancellation_rate': cancellation_rate,
        'refund_rate': refund_rate,
        'success_rate': success_rate,
        'txn_status_counts_json': json.dumps([success_count, cancelled_count, failed_count, refunded_count]),

        # User Growth
        'total_users_count': total_users_count,
        'new_users_period': new_users_period,
        'active_booking_users': active_booking_users,
        'user_growth_dates_json': json.dumps(user_growth_dates),
        'user_growth_counts_json': json.dumps(user_growth_counts),
    }

    return render(request, 'admin/dashboard.html', context)


@login_required(login_url='/login/')
@user_passes_test(is_admin_user, login_url='/login/', redirect_field_name='next')
def export_dashboard_csv(request, report_type):
    """
    Exports filtered analytics reports as downloadable CSV spreadsheets.
    Supported report_type: 'revenue', 'bookings', 'theaters', 'cancellations'.
    """
    start_dt, end_dt, start_date_str, end_date_str, _ = get_date_range(request)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)

    if report_type == 'revenue':
        response['Content-Disposition'] = f'attachment; filename="revenue_report_{timestamp}.csv"'
        writer.writerow(['Date', 'Total Orders', 'Successful Bookings Amount (INR)', 'Cancelled Amount (INR)', 'Failed Orders'])

        rows = (
            PaymentTransaction.objects.filter(created_at__range=(start_dt, end_dt))
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total_orders=Count('id'),
                success_amount=Coalesce(Sum('amount', filter=Q(status=PaymentTransaction.STATUS_SUCCESS)), Value(Decimal('0.00'))),
                cancelled_amount=Coalesce(Sum('amount', filter=Q(status=PaymentTransaction.STATUS_CANCELLED)), Value(Decimal('0.00'))),
                failed_count=Count('id', filter=Q(status=PaymentTransaction.STATUS_FAILED))
            )
            .order_by('date')
        )
        for r in rows:
            writer.writerow([r['date'], r['total_orders'], f"{r['success_amount']:.2f}", f"{r['cancelled_amount']:.2f}", r['failed_count']])

    elif report_type == 'bookings':
        response['Content-Disposition'] = f'attachment; filename="bookings_manifest_{timestamp}.csv"'
        writer.writerow(['Booking ID', 'Username', 'Email', 'Movie', 'Theater', 'City', 'Seat Number', 'Ticket Price (INR)', 'Booked At', 'Payment Reference'])

        bookings = (
            Booking.objects.filter(booked_at__range=(start_dt, end_dt))
            .select_related('user', 'movie', 'theater', 'seat', 'payment')
            .order_by('-booked_at')[:5000]
        )
        for b in bookings:
            writer.writerow([
                str(b.booking_id),
                b.user.username,
                b.user.email,
                b.movie.name,
                b.theater.name,
                b.theater.city,
                b.seat.seat_number,
                f"{b.theater.ticket_price:.2f}",
                b.booked_at.strftime('%Y-%m-%d %H:%M:%S'),
                b.payment_reference or 'N/A'
            ])

    elif report_type == 'theaters':
        response['Content-Disposition'] = f'attachment; filename="theater_occupancy_{timestamp}.csv"'
        writer.writerow(['Theater Name', 'Movie', 'City', 'Showtime', 'Ticket Price (INR)', 'Total Seats', 'Booked Seats', 'Available Seats', 'Occupancy (%)', 'Period Revenue (INR)'])

        theaters = (
            Theater.objects.select_related('movie')
            .annotate(
                total_seats=Count('seats', distinct=True),
                booked_seats=Count('seats', filter=Q(seats__is_booked=True), distinct=True),
                period_revenue=Coalesce(
                    Sum('bookings__payment__amount', filter=Q(
                        bookings__booked_at__range=(start_dt, end_dt),
                        bookings__payment__status=PaymentTransaction.STATUS_SUCCESS
                    )),
                    Value(Decimal('0.00'))
                )
            )
            .order_by('-period_revenue')
        )
        for t in theaters:
            total_seats = t.total_seats
            booked_seats = t.booked_seats
            avail = max(0, total_seats - booked_seats)
            occ = round((booked_seats / total_seats * 100), 1) if total_seats > 0 else 0.0
            writer.writerow([
                t.name,
                t.movie.name,
                t.city,
                t.time.strftime('%Y-%m-%d %H:%M'),
                f"{t.ticket_price:.2f}",
                total_seats,
                booked_seats,
                avail,
                f"{occ}%",
                f"{t.period_revenue:.2f}"
            ])

    elif report_type == 'cancellations':
        response['Content-Disposition'] = f'attachment; filename="cancellations_refunds_{timestamp}.csv"'
        writer.writerow(['Order ID', 'Transaction ID', 'Username', 'Amount (INR)', 'Status', 'Error Code', 'Reason / Description', 'Created At'])

        txns = (
            PaymentTransaction.objects.filter(
                created_at__range=(start_dt, end_dt),
                status__in=[PaymentTransaction.STATUS_CANCELLED, PaymentTransaction.STATUS_FAILED, PaymentTransaction.STATUS_REFUNDED]
            )
            .select_related('user')
            .order_by('-created_at')[:5000]
        )
        for t in txns:
            writer.writerow([
                t.order_id,
                str(t.transaction_id),
                t.user.username,
                f"{t.amount:.2f}",
                t.status,
                t.error_code or 'N/A',
                t.error_description or 'User / System Cancelled',
                t.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

    else:
        raise Http404("Invalid report type specified.")

    return response
