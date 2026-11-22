#!/bin/sh
# Replace one database from a SQL dump. The Docker volume is left in place.
set -eu
cd "$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
. ./scripts/db_env.sh

if [ "${GD_OS_RESTORE_CONFIRM:-}" != "yes" ]; then
  echo "Refusing to restore. Set GD_OS_RESTORE_CONFIRM=yes to replace the target database." >&2
  exit 2
fi

file=${1:-}
if [ -z "$file" ] || [ ! -s "$file" ]; then
  echo "Usage: scripts/restore.sh BACKUP.sql [database]" >&2
  exit 2
fi

user=$(read_env POSTGRES_USER gdos)
target=${2:-$(read_env POSTGRES_DB gdos)}

case "$target" in
  postgres|template0|template1)
    echo "Refusing to replace the $target database." >&2
    exit 2
    ;;
esac

printf '%s' "$target" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*$' || {
  echo "The database name must be letters, numbers, and underscores." >&2
  exit 2
}

docker compose exec -T postgres psql -U "$user" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${target}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "${target}";
CREATE DATABASE "${target}";
SQL

docker compose exec -T postgres psql -U "$user" -d "$target" -v ON_ERROR_STOP=1 < "$file"
echo "Restored ${file} into ${target}"
