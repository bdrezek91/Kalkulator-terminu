import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Tworzy konto administratora na podstawie zmiennych środowiskowych "
        "DJANGO_ADMIN_USERNAME / DJANGO_ADMIN_EMAIL / DJANGO_ADMIN_PASSWORD, "
        "jeśli jeszcze nie istnieje. Nie robi nic, jeśli zmienne nie są ustawione "
        "lub konto już istnieje."
    )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_ADMIN_USERNAME")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD")
        email = os.environ.get("DJANGO_ADMIN_EMAIL", "")

        if not username or not password:
            self.stdout.write(
                "Pomijam tworzenie administratora — brak DJANGO_ADMIN_USERNAME/DJANGO_ADMIN_PASSWORD w środowisku."
            )
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Użytkownik '{username}' już istnieje — pomijam.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Utworzono konto administratora '{username}'."))
