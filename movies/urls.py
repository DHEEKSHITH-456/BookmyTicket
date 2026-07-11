from django.urls import path
from . import views
urlpatterns = [
    path('', views.movie_list, name='movie_list'),
    path('<int:movie_id>/', views.theater_list, name='theater_list'), 
    path('theaters/<int:movie_id>/', views.theater_list, name='theater_list'),
    path('seats/<int:theater_id>/', views.seat_selection, name='seat_selection'),
]