from django.urls import path
from . import views

urlpatterns = [
    path('', views.movie_list, name='movie_list'),
    path('<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('<int:movie_id>/theaters/', views.theater_list, name='theater_list'),
    path('theater/<int:theater_id>/seats/book/', views.book_seats, name='book_seats'),
    path('theater/<int:theater_id>/seats/live/', views.live_seat_status, name='live_seat_status'),
    path('payment/checkout/<str:order_id>/', views.payment_checkout, name='payment_checkout'),
    path('payment/modify/<str:order_id>/', views.modify_seats, name='modify_seats'),
    path('payment/verify/', views.payment_verify, name='payment_verify'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
    path('payment/cancel/<str:order_id>/', views.payment_cancel, name='payment_cancel'),
    path('payment/webhook/', views.payment_webhook, name='payment_webhook'),
    path('booking/<uuid:booking_id>/confirmation/', views.booking_confirmation, name='booking_confirmation'),
    path('booking/<uuid:booking_id>/download-ticket/', views.download_ticket, name='download_ticket'),
]