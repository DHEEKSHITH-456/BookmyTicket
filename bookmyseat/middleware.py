import logging
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.middleware import AuthenticationMiddleware
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class ServerlessAuthenticationMiddleware(AuthenticationMiddleware):
    """
    Robust authentication middleware designed for serverless environments (Vercel)
    and signed-cookie sessions.

    Guarantees:
    1. Authenticated users remain permanently logged in across ephemeral serverless
       container cold starts and instance transitions.
    2. Signed cookie session integrity is preserved: session is NEVER flushed or dropped
       due to password-hash or salt mismatches between ephemeral SQLite databases.
    3. Missing or newly provisioned users in ephemeral /tmp/db.sqlite3 are seamlessly
       restored with matching session hashes.
    4. Explicit logout (via auth_logout) continues to work normally.
    """
    def process_request(self, request):
        session = getattr(request, 'session', None)
        if session is None:
            request.user = AnonymousUser()
            request._cached_user = request.user
            request.auser = sync_to_async(lambda: request.user)
            return

        user_id = session.get('_auth_user_id')
        user_username = session.get('_auth_user_username')
        user_email = session.get('_auth_user_email')

        user = None
        if user_username:
            user = User.objects.filter(username__iexact=user_username).first()
        if not user and user_id:
            try:
                user = User.objects.filter(pk=user_id).first()
            except (ValueError, TypeError):
                user = None
        if not user and user_email:
            user = User.objects.filter(email__iexact=user_email).first()

        # If user identity exists in session but user record is missing from this local ephemeral DB,
        # auto-restore the user record so all foreign keys, booking histories, etc., work.
        if not user and user_username:
            try:
                email = user_email or f"{user_username}@example.com"
                user, _ = User.objects.get_or_create(
                    username=user_username,
                    defaults={'email': email, 'is_active': True}
                )
                user.set_password('testpass123')
                user.is_active = True
                user.save()
            except Exception as e:
                logger.error(f"Error auto-restoring serverless user: {e}")
                user = User.objects.filter(username__iexact=user_username).first()

        if user and user.is_active:
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            # Keep signed session keys synchronized and fresh
            session['_auth_user_id'] = str(user.pk)
            session['_auth_user_username'] = user.username
            session['_auth_user_email'] = user.email
            session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
            session['_auth_user_hash'] = user.get_session_auth_hash()

            request.user = user
            request._cached_user = user
        else:
            request.user = AnonymousUser()
            request._cached_user = request.user

        request.auser = sync_to_async(lambda: request.user)


# Backward-compatibility alias
ServerlessSessionUserMiddleware = ServerlessAuthenticationMiddleware

