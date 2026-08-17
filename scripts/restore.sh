#!/bin/sh
# Odtwarza bazę PostgreSQL z kopii zapasowej utworzonej przez backup.sh.
# UWAGA: nadpisuje bieżącą zawartość bazy danych.
# Użycie: ./scripts/restore.sh backups/kalkulator_20260101_120000.sql.gz
set -e

cd "$(dirname "$0")/.."

if [ -z "$1" ]; then
    echo "Użycie: $0 <plik_kopii.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Plik $BACKUP_FILE nie istnieje."
    exit 1
fi

if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

echo "UWAGA: to nadpisze bieżącą zawartość bazy '${POSTGRES_DB:-kalkulator}'."
printf "Kontynuować? [t/N] "
read -r CONFIRM
if [ "$CONFIRM" != "t" ] && [ "$CONFIRM" != "T" ]; then
    echo "Przerwano."
    exit 0
fi

gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U "${POSTGRES_USER:-kalkulator}" "${POSTGRES_DB:-kalkulator}"
echo "Odtwarzanie zakończone."
