#!/bin/sh
# Write a plain SQL dump of the café database. This does not stop the API.
set -eu
cd "$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
. ./scripts/db_env.sh

user=$(read_env POSTGRES_USER gdos)
db=$(read_env POSTGRES_DB gdos)
mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
out="backups/${db}-${stamp}.sql"
partial="${out}.partial"

docker compose exec -T postgres pg_dump -U "$user" -d "$db" --no-owner --no-acl > "$partial"
if [ ! -s "$partial" ]; then
  rm -f "$partial"
  echo "Backup file is empty" >&2
  exit 1
fi
mv "$partial" "$out"
echo "$out"
