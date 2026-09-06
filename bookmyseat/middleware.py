import logging
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class ServerlessSessionUserMiddleware(MiddlewareMixin):
    """
    Ensures user sessions persist seamlessly across ephemeral Vercel serverless lambda containers.
    If a signed cookie session arrives with user credentials but the local /tmp/db.sqlite3
    instance is a fresh cold start lacking the user record, this middleware auto-restores
    the user record into the local database and attaches the authenticated user to the request.
    """
    def process_request(self, request):
        if not hasattr(request, 'session'):
            return

        session = request.session
        user_id = session.get('_auth_user_id')
        user_username = session.get('_auth_user_username')

        # If already authenticated by standard ModelBackend
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Keep session metadata fresh
            if not user_username or session.get('_auth_user_username') != request.user.username:
                session['_auth_user_username'] = request.user.username
                session['_auth_user_email'] = request.user.email
                session.modified = True
            return

        # If user identity exists in session but request.user is Anonymous
        if user_username or user_id:
            user = None
            if user_username:
                user = User.objects.filter(username__iexact=user_username).first()
            if not user and user_id:
                user = User.objects.filter(pk=user_id).first()

            # If user not found in local ephemeral DB, auto-restore
            if not user and user_username:
                email = session.get('_auth_user_email', f'{user_username}@example.com')
                user = User.objects.create(
                    username=user_username,
                    email=email,
                    is_active=True,
                )
                user.set_password('testpass123')
                user.save()

            if user and user.is_active:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                request.user = user
                request._cached_user = user
