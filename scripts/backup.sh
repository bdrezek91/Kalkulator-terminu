#!/bin/sh
# Wykonuje kopię zapasową bazy PostgreSQL z kontenera "db" do katalogu ./backups.
# Użycie: ./scripts/backup.sh [nazwa_pliku.sql.gz]
set -e

cd "$(dirname "$0")/.."
mkdir -p backups

if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="${1:-backups/kalkulator_${TIMESTAMP}.sql.gz}"

echo "Tworzę kopię zapasową bazy '${POSTGRES_DB:-kalkulator}' do ${FILENAME}..."
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-kalkulator}" "${POSTGRES_DB:-kalkulator}" | gzip > "${FILENAME}"
echo "Gotowe: ${FILENAME}"
