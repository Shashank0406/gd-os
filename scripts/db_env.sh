# Shared by the backup and restore scripts. Do not print values from .env.

read_env() {
  key=$1
  fallback=$2
  if [ ! -f .env ]; then
    printf '%s' "$fallback"
    return
  fi
  line=$(grep -E "^${key}=" .env | head -n 1 || true)
  if [ -z "$line" ]; then
    printf '%s' "$fallback"
    return
  fi
  printf '%s' "${line#*=}"
}
