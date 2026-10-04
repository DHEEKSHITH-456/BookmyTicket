import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from movies.payment_service import release_expired_reservations
from movies.models import Seat


class Command(BaseCommand):
    help = "Task 5: Automatically release expired 2-minute seat reservations in the background."

    def add_arguments(self, parser):
        parser.add_argument(
            '--loop',
            action='store_true',
            help='Run continuously as a background daemon process.',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='Polling interval in seconds when running in loop mode (default: 10s).',
        )

    def handle(self, *args, **options):
        loop_mode = options.get('loop', False)
        interval = options.get('interval', 10)

        if loop_mode:
            self.stdout.write(self.style.SUCCESS(
                f"Starting background seat cleanup worker (polling every {interval}s)... Press Ctrl+C to exit."
            ))
            try:
                while True:
                    released = release_expired_reservations()
                    if released > 0:
                        self.stdout.write(self.style.WARNING(
                            f"[{timezone.now().strftime('%H:%M:%S')}] Released {released} expired seat reservation(s)."
                        ))
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.NOTICE("\nBackground seat cleanup worker stopped."))
        else:
            released = release_expired_reservations()
            if released > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully released {released} expired seat reservation(s)."
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    "No expired seat reservations found (0 seats released)."
                ))
