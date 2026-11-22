#!/bin/sh
# Dump the running database and restore that dump into a separate database.
set -eu
cd "$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
. ./scripts/db_env.sh

user=$(read_env POSTGRES_USER gdos)
db=$(read_env POSTGRES_DB gdos)
check=gdos_restore_check

out=$(sh scripts/backup.sh)
echo "dump=$out"
grep -q "CREATE TABLE public.stations" "$out"
grep -q "150.00" "$out"

set +e
sh scripts/restore.sh "$out" "$check"
refused=$?
set -e
if [ "$refused" -ne 2 ]; then
  echo "Restore without confirmation exited $refused" >&2
  exit 1
fi

exists=$(docker compose exec -T postgres psql -U "$user" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${check}'")
if [ "$exists" = "1" ]; then
  echo "Unconfirmed restore created ${check}" >&2
  exit 1
fi

live=$(docker compose exec -T postgres psql -U "$user" -d "$db" -tAc "SELECT count(*) FROM stations")
if [ "$live" != "21" ]; then
  echo "Live station count changed: $live" >&2
  exit 1
fi

GD_OS_RESTORE_CONFIRM=yes sh scripts/restore.sh "$out" "$check"
restored=$(docker compose exec -T postgres psql -U "$user" -d "$check" -tAc "SELECT count(*) FROM stations")
rate=$(docker compose exec -T postgres psql -U "$user" -d "$check" -tAc "SELECT hourly_rate_rupees FROM pricing_plans WHERE name = 'Gaming PC default' AND station_id IS NULL")
docker compose exec -T postgres psql -U "$user" -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE ${check}"

if [ "$restored" != "21" ]; then
  echo "Restored station count was $restored" >&2
  exit 1
fi
if [ "$rate" != "150.00" ]; then
  echo "Restored PC rate was $rate" >&2
  exit 1
fi
echo "backup restore ok"
