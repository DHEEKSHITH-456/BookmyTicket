from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .forms import UserRegisterForm, UserUpdateForm
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from movies.models import Movie, Booking
from movies.views import get_recommended_movies


def home(request):
    movies = Movie.objects.all().order_by('-popularity')
    recommended_movies = get_recommended_movies(request)
    return render(request, 'home.html', {
        'movies': movies,
        'recommended_movies': recommended_movies,
    })


def register(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Specify backend to ensure login succeeds without re-authenticating
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Welcome, {user.username}! Your account has been created successfully.')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('movie_list')

    if request.method == 'POST':
        # Support login by Username OR Email
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Check if entered text is an email
        user_obj = None
        if '@' in username_or_email:
            matched_user = User.objects.filter(email__iexact=username_or_email).first()
            if matched_user:
                username_or_email = matched_user.username

        user = authenticate(request, username=username_or_email, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                next_url = request.GET.get('next') or request.POST.get('next') or 'movie_list'
                return redirect(next_url)
            else:
                messages.error(request, 'Your account has been deactivated. Please contact support.')
        else:
            form = AuthenticationForm(request, data=request.POST)
            # Add explicit user-friendly error
            messages.error(request, 'Invalid username/email or password. Please verify your credentials and try again.')
            return render(request, 'users/login.html', {
                'form': form,
                'error': 'Invalid username/email or password.',
                'username_val': request.POST.get('username', ''),
            })
    else:
        form = AuthenticationForm()

    return render(request, 'users/login.html', {'form': form})


@login_required
def profile(request):
    bookings = Booking.objects.filter(user=request.user).select_related(
        'movie', 'theater', 'seat'
    ).order_by('-booked_at')
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        if u_form.is_valid():
            u_form.save()
            messages.success(request, 'Your profile details have been updated successfully.')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)

    return render(request, 'users/profile.html', {
        'u_form': u_form,
        'bookings': bookings,
    })


@login_required
def reset_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'users/reset_password.html', {'form': form})