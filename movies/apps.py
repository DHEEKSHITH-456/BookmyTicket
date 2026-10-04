import os
import sys
import threading
import time
from django.apps import AppConfig


class MoviesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'movies'

    def ready(self):
        """
        Task 5: Start persistent in-process background worker daemon for automatic seat expiry.
        Ensures expired reservations are cleaned up every 10 seconds even if Celery Beat
        is not running and no HTTP requests are arriving.
        """
        is_manage_py = any('manage.py' in arg for arg in sys.argv)
        is_runserver = 'runserver' in sys.argv
        skip_commands = {'migrate', 'makemigrations', 'collectstatic', 'check', 'showmigrations'}
        is_maintenance = any(cmd in sys.argv for cmd in skip_commands)

        if is_maintenance:
            return

        should_start = (
            (is_runserver and os.environ.get('RUN_MAIN') == 'true') or
            (not is_manage_py)  # WSGI / Gunicorn / ASGI
        )

        if should_start and not getattr(self, '_daemon_started', False):
            self._daemon_started = True
            self._start_cleanup_worker()

    def _start_cleanup_worker(self):
        def _cleanup_loop():
            # Initial grace period on startup
            time.sleep(3)
            while True:
                try:
                    from movies.payment_service import release_expired_reservations
                    release_expired_reservations()
                except Exception:
                    pass
                time.sleep(10)

        t = threading.Thread(target=_cleanup_loop, daemon=True, name="SeatReservationCleanupWorker")
        t.start()

