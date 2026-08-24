# Kalkulator terminu pawilonu

Aplikacja webowa (Django + PostgreSQL) do wyznaczania najwcześniejszego
bezpiecznego tygodnia realizacji nowego pawilonu na podstawie aktualnej
kolejki produkcyjnej, wyposażenia i mocy brygad.

- **Publiczny kalkulator** — bez logowania, dla handlowców.
- **Panel administratora** — logowanie Django, import pełnych eksportów XLSX
  z Comarch ERP Optima, podgląd walidacji, historia importów, edycja
  konfiguracji mocy produkcyjnych i czasów operacji.

## Spis treści

- [Wymagania](#wymagania)
- [Uruchomienie lokalne (Docker Compose)](#uruchomienie-lokalne-docker-compose)
- [Uruchomienie lokalne (bez Dockera, do developmentu)](#uruchomienie-lokalne-bez-dockera-do-developmentu)
- [Pierwsze kroki po uruchomieniu](#pierwsze-kroki-po-uruchomieniu)
- [Testy](#testy)
- [Aktualizacja bez utraty danych](#aktualizacja-bez-utraty-danych)
- [Kopia zapasowa i odtwarzanie](#kopia-zapasowa-i-odtwarzanie)
- [Struktura projektu](#struktura-projektu)
- [Bezpieczeństwo](#bezpieczeństwo)
- [Znane ograniczenia MVP](#znane-ograniczenia-mvp)
- [Dane potrzebne przed wdrożeniem produkcyjnym](#dane-potrzebne-przed-wdrożeniem-produkcyjnym)

## Wymagania

- Docker + Docker Compose (zalecane do uruchomienia produkcyjnego/testowego).
- Do developmentu bez Dockera: Python 3.12, PostgreSQL 16 (lub lokalny SQLite do szybkich testów).

## Uruchomienie lokalne (Docker Compose)

```bash
cp .env.example .env
# edytuj .env — ustaw POSTGRES_PASSWORD, DJANGO_SECRET_KEY i pozostałe wartości

docker compose up -d --build
```

Aplikacja będzie dostępna pod `http://localhost:8010/` (port konfigurowalny
zmienną `WEB_PORT` w `.env`). Baza PostgreSQL **nie** wystawia portu na hosta.

Przy pierwszym starcie kontener `web` automatycznie:
1. czeka na dostępność bazy danych,
2. wykonuje migracje,
3. zbiera pliki statyczne,
4. wgrywa domyślną konfigurację (brygady, czasy operacji, moce produkcyjne),
5. tworzy konto administratora, jeśli w `.env` ustawiono
   `DJANGO_ADMIN_USERNAME` / `DJANGO_ADMIN_EMAIL` / `DJANGO_ADMIN_PASSWORD`.

Jeśli nie ustawiłeś tych zmiennych, utwórz konto administratora ręcznie:

```bash
docker compose exec app python manage.py createsuperuser
```

## Uruchomienie lokalne (bez Dockera, do developmentu)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# do szybkiego developmentu można ustawić w .env:
# DATABASE_URL=sqlite:///db.sqlite3
# DJANGO_DEBUG=True

python manage.py migrate
python manage.py seed_defaults
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8010
```

## Pierwsze kroki po uruchomieniu

1. Wejdź na `http://localhost:8010/admin-panel/login/` i zaloguj się kontem administratora.
2. W panelu przejdź do **Nowy import XLSX** i wgraj pełny eksport „Lista zasobów” z Optimy.
3. Sprawdź podgląd walidacji (statystyki, konflikty, nierozpoznane wartości).
4. Zatwierdź import — staje się nową aktywną migawką (poprzednia zostaje zachowana do audytu).
5. Wejdź na stronę główną `http://localhost:8010/` i sprawdź działanie publicznego kalkulatora.
6. W razie potrzeby dostosuj czasy operacji, moce produkcyjne, bufor i ręczne
   korekty backlogu w panelu Django pod `/django-admin/pawilony/`.

## Testy

```bash
# w środowisku lokalnym (venv)
python -m pytest

# w kontenerze
docker compose exec app python -m pytest
```

Zestaw testów (75 testów) obejmuje m.in.: normalizację wartości (`{pusty}`,
duplikaty, `_x000d_`), klasyfikację statusów (aktywny/zakończony/nierozpoznany/
konflikt), parser modułów (wszystkie wymagane warianty zapisu i moduły 2+),
liczenie godzin brygad (hydraulika, spawacze, FIBO/boazeria, równoległość
brygad), bufor 15% i pojemność 38,25 bez przedwczesnego zaokrąglenia, przejście
tygodnia ISO przez przełom roku, transakcyjność importu, duplikaty aktywnego
kodu, ostrzeżenie o braku kolumn FIBO/boazeria, brak dostępu anonimowego do
panelu administratora, brak wycieku numerów projektów na stronie publicznej —
oraz **test akceptacyjny na kopii wzorcowego pliku** `fixtures/wykaz_pawilonow_wzorcowy.xlsx`
(4447 wierszy, plik nigdy nie jest modyfikowany, tylko odczytywany).

## Wdrożenie za współdzielonym reverse proxy (Caddy w Dockerze)

Jeśli na VPS masz już działający kontener Caddy obsługujący inne aplikacje
(porty 80/443 zajęte przez ten kontener), **nie** wystawiaj portu kalkulatora
publicznie — zamiast tego podłącz Caddy do sieci Docker naszej aplikacji.

1. **Sklonuj repo i skonfiguruj `.env`** jak w sekcji wyżej. Dodatkowo ustaw:
   ```
   DJANGO_ALLOWED_HOSTS=kalkulator.twojadomena.pl
   DJANGO_CSRF_TRUSTED_ORIGINS=https://kalkulator.twojadomena.pl
   ```
2. **Zbuduj i uruchom stos** (bez publicznego portu — `web` nasłuchuje tylko na `127.0.0.1`):
   ```bash
   docker compose up -d --build
   curl -I http://127.0.0.1:8010/   # powinno zwrócić 200 OK
   ```
3. **Podłącz istniejący kontener Caddy do sieci kalkulatora**, żeby mógł
   rozwiązać nazwę `kalkulator-web` przez DNS Dockera (nie trzeba restartować
   Caddy — dołączenie do sieci działa "na żywo"):
   ```bash
   docker network connect kalkulator_default <nazwa_kontenera_caddy>
   # np.: docker network connect kalkulator_default multiplekser-caddy-1
   ```
4. **Dopisz nowy blok domeny do `Caddyfile`** używanego przez ten kontener
   (znajdziesz ścieżkę przez `docker inspect <kontener_caddy> --format '{{json .Mounts}}'`),
   **nie usuwając** istniejących wpisów dla innych aplikacji:
   ```caddyfile
   kalkulator.twojadomena.pl {
       reverse_proxy kalkulator-web:8000
   }
   ```
5. **Przeładuj konfigurację Caddy bez przerywania innych stron**:
   ```bash
   docker exec <nazwa_kontenera_caddy> caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
   ```
6. **Ustaw rekord DNS A** dla `kalkulator.twojadomena.pl` na publiczne IP VPS
   (jeśli jeszcze nie istnieje). Caddy automatycznie wystawi certyfikat Let's
   Encrypt przy pierwszym żądaniu HTTPS.
7. **Test end-to-end**: `https://kalkulator.twojadomena.pl/` (kalkulator
   publiczny) i `https://kalkulator.twojadomena.pl/admin-panel/login/`
   (panel administratora).

Ustawienie `SECURE_PROXY_SSL_HEADER` w `config/settings.py` jest już
skonfigurowane pod ten scenariusz — Django prawidłowo rozpozna żądania jako
bezpieczne (https) na podstawie nagłówka `X-Forwarded-Proto` przekazywanego
przez Caddy, zamiast wpaść w pętlę przekierowań.

> **Uwaga na kolizje nazw usług.** Gdy współdzielony kontener Caddy zostanie
> podłączony do kilku sieci Docker jednocześnie (np. sieci innej aplikacji
> i sieci `kalkulator_default`), rozwiązywanie DNS krótkiej nazwy usługi
> (nie `container_name`, tylko klucz usługi z `docker-compose.yml`, np. `web`)
> staje się niejednoznaczne, jeśli dwie różne aplikacje mają usługę o tej
> samej nazwie — Caddy może trafić do złego kontenera. Dlatego usługa
> aplikacji nazywa się tu `app` (nie `web`), a `reverse_proxy` w Caddyfile
> powinien zawsze celować w unikalny `container_name` (`kalkulator-web`),
> nigdy w gołą nazwę usługi. Jeśli na tym samym VPS stoją inne stosy Compose
> podłączane do wspólnego Caddy, sprawdź, czy żadna z ich usług nie nazywa
> się tak samo jak Twoje (`app`, `db`) — w razie kolizji zmień nazwę usługi
> w `docker-compose.yml` na coś unikalnego dla tego serwera.

### Wariant: wspólna domena z prefiksem ścieżki (bez osobnej subdomeny)

Jeśli zamiast osobnej subdomeny (`kalkulator.twojadomena.pl`) kalkulator ma
być wystawiony pod ścieżką na już istniejącej domenie (np.
`twojadomena.pl/kalkulator-terminu/`), Caddyfile musi zdjąć prefiks przed
przekazaniem żądania dalej (`handle_path`), bo aplikacja Django nie wie nic
o prefiksie i sama liczy się od "/":

```caddyfile
twojadomena.pl {
    handle_path /kalkulator-terminu/* {
        reverse_proxy kalkulator-web:8000
    }
    # Kalkulator serwuje statyki (Whitenoise) pod bezwzględnym /static/,
    # niezależnie od prefiksu ścieżki, na jakiej stoi strona — dlatego
    # osobny blok bez zdejmowania prefiksu.
    handle /static/* {
        reverse_proxy kalkulator-web:8000
    }
    handle {
        reverse_proxy <inna-aplikacja-na-tej-domenie>
    }
}
```

**To nie wystarczy samo w sobie.** Bez dodatkowej konfiguracji po stronie
Django wszystkie linki generowane przez `{% url %}`/`reverse()`/`redirect()`
(np. „Logowanie administratora", panel Django-admin) będą bezwzględne od
korzenia domeny (`/admin-panel/login/`), a nie `/kalkulator-terminu/admin-panel/login/`
— Caddy nie dopasuje takiego żądania do reguły kalkulatora i klient trafi do
**innej aplikacji** wystawionej na tej samej domenie (`handle { ... }` na
końcu). Ustaw w `.env`:

```
DJANGO_FORCE_SCRIPT_NAME=/kalkulator-terminu
```

`FORCE_SCRIPT_NAME` dopisuje ten prefiks do wszystkich URL-i generowanych
przez Django (nie dotyczy `STATIC_URL`/Whitenoise — te zostają pod
bezwzględnym `/static/`, zgodnie z osobnym blokiem `handle /static/*`
powyżej). Zostaw tę zmienną pustą/niewpisaną w wariancie z osobną subdomeną.

## Aktualizacja bez utraty danych

```bash
git pull
docker compose build app
docker compose up -d app
# entrypoint kontenera automatycznie wykona nowe migracje przy starcie
```

Wolumeny `postgres_data` i `media_data` nie są usuwane przy `docker compose up`
ani `docker compose build` — dane przetrwają restart i aktualizację. Nie
używaj `docker compose down -v` w produkcji (usuwa wolumeny!).

## Kopia zapasowa i odtwarzanie

```bash
# kopia zapasowa (zapisuje do backups/kalkulator_TIMESTAMP.sql.gz)
./scripts/backup.sh

# odtworzenie z kopii (NADPISUJE bieżącą bazę — wymaga potwierdzenia)
./scripts/restore.sh backups/kalkulator_20260101_120000.sql.gz
```

Zaleca się regularne (np. codzienne) uruchamianie `scripts/backup.sh` przez
cron na hoście i przechowywanie kopii poza serwerem.

## Struktura projektu

```
config/                     ustawienia Django, urls, wsgi/asgi
pawilony/
  models.py                 modele danych (ImportBatch, PavilionSnapshot, ...)
  services/                 logika biznesowa (normalizacja, statusy, moduły,
                             godziny, import, moce produkcyjne, tydzień ISO)
  views.py, forms.py, urls.py
  admin.py                  rejestracja modeli w panelu Django
  templates/pawilony/       szablony HTML (Bootstrap 5)
  management/commands/      seed_defaults, bootstrap_admin
  tests/                    testy jednostkowe i integracyjne
fixtures/                   kopia wzorcowego pliku XLSX do testu akceptacyjnego
scripts/                    entrypoint.sh, backup.sh, restore.sh
Dockerfile, docker-compose.yml, .env.example
```

## Bezpieczeństwo

- Publiczny kalkulator nie wymaga konta; import i konfiguracja wymagają
  zalogowanego administratora (`@login_required` / `LoginRequiredMixin`).
- CSRF, bezpieczne cookies (`Secure`, `HttpOnly` dla sesji) i nagłówki
  bezpieczeństwa (HSTS, `X-Frame-Options: DENY`, `nosniff`) włączone
  automatycznie, gdy `DJANGO_DEBUG=False`.
- Upload ograniczony do plików `.xlsx`, z limitem rozmiaru
  (`IMPORT_MAX_UPLOAD_SIZE_MB`, domyślnie 15 MB); nazwy plików generowane są
  bezpiecznie (UUID), nazwa od użytkownika nigdy nie trafia na dysk.
- Plik XLSX jest odczytywany przez `openpyxl` (bez wykonywania makr — format
  `.xlsx` ich nie zawiera).
- Kontener PostgreSQL nie wystawia portu na hosta.
- Healthcheck dla `web` (HTTP) i `db` (`pg_isready`).
- Podstawowy rate limiting publicznego formularza kalkulatora (domyślnie 30
  żądań/60s na adres IP, konfigurowalny w `.env`).
- Działania administracyjne (zatwierdzenie/odrzucenie importu) są logowane
  (logger `pawilony.audit`).

## Znane ograniczenia MVP

- Brak bezpośredniej synchronizacji z Optimą — import jest ręczny (plik XLSX).
- Brak automatycznej kontroli zapłaty proformy i rezerwacji terminu (modele
  `Reservation`/`Proforma` przygotowane jako szkielet pod przyszłą funkcję,
  ale nieaktywne w żadnym widoku).
- Brak kont handlowców — kalkulator jest w pełni anonimowy.
- `TERMIN REALIZ.` z importu jest zachowywany, ale nie wpływa na kalkulację
  (żaden pawilon nie jest traktowany jako częściowo wykonany).
- Eksport z Optimy może obecnie nie zawierać kolumn FIBO/BOAZERIA — w takim
  przypadku aplikacja pokazuje wyraźne ostrzeżenie (publicznie i w podglądzie
  importu), dopóki administrator nie ustawi ręcznej korekty backlogu dla tej
  brygady.
- Rate limiting działa w pamięci procesu (`LocMemCache`) — przy wielu
  workerach/instancjach limit jest per-proces, nie globalny; do pełnej
  ochrony w większej skali warto podłączyć Redis jako backend cache.

## Dane potrzebne przed wdrożeniem produkcyjnym

- Docelowa domena i certyfikat TLS (oraz konfiguracja reverse proxy —
  nie została wykonana w ramach tego zadania, zgodnie z poleceniem, aby nie
  ingerować w istniejącą infrastrukturę bez potwierdzenia).
- Rzeczywiste, bezpieczne hasła: `POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY`,
  dane konta administratora.
- Potwierdzenie wolnego portu na hoście dla `WEB_PORT` (domyślnie 8010).
- Docelowe wartości konfiguracji mocy produkcyjnych (jeśli inne niż podane
  w specyfikacji: 45 pawilonów/tydzień, 8 hydraulików, 8 spawaczy, 3 os.
  FIBO/boazeria, 40 h/tydzień, bufor 15%).
- Docelowy próg nieaktualności danych (domyślnie 24 h) i limit rozmiaru
  uploadu (domyślnie 15 MB), jeśli mają być inne.
- Harmonogram i miejsce docelowe przechowywania kopii zapasowych
  (`scripts/backup.sh` zapisuje lokalnie do `backups/` — do produkcji zalecane
  jest dogranie kopii do zewnętrznego storage).
