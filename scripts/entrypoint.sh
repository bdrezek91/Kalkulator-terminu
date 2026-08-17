#!/bin/sh
set -e

echo "Czekam na bazę danych PostgreSQL..."
python - <<'PYEOF'
import os
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connections
from django.db.utils import OperationalError

for attempt in range(30):
    try:
        connections["default"].cursor()
        print("Baza danych jest dostępna.")
        sys.exit(0)
    except OperationalError:
        print(f"Baza niedostępna, próba {attempt + 1}/30...")
        time.sleep(2)

print("Nie udało się połączyć z bazą danych.")
sys.exit(1)
PYEOF

echo "Wykonuję migracje..."
python manage.py migrate --noinput

echo "Zbieram pliki statyczne..."
python manage.py collectstatic --noinput

echo "Wgrywam domyślną konfigurację (jeśli brak)..."
python manage.py seed_defaults

echo "Tworzę konto administratora (jeśli skonfigurowano zmienne środowiskowe)..."
python manage.py bootstrap_admin

exec "$@"
