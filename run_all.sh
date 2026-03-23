#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

if [[ -d ".venv" && -f ".venv/bin/activate" ]]; then
  source ".venv/bin/activate"
fi

if [[ ! -f "manage.py" ]]; then
  echo "Error: manage.py not found in $PROJECT_ROOT"
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
RESET_DB="${RESET_DB:-1}"
RUN_SEED="${RUN_SEED:-1}"

if [[ "$RESET_DB" == "1" ]]; then
  echo "Resetting database to a clean state..."

  ROOT_DB_PATH="$PROJECT_ROOT/db.sqlite3"
  if [[ -f "$ROOT_DB_PATH" ]]; then
    rm -f "$ROOT_DB_PATH"
    echo "Deleted SQLite database: $ROOT_DB_PATH"
  fi

  DB_PATH="$($PYTHON_BIN - <<'PY'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resolveme.settings")
from django.conf import settings
db = settings.DATABASES.get("default", {})
if db.get("ENGINE", "").endswith("sqlite3"):
  db_name = db.get("NAME", "")
  print(str(db_name).strip())
PY
)"

  if [[ -n "$DB_PATH" ]]; then
    if [[ "$DB_PATH" != /* ]]; then
      DB_PATH="$PROJECT_ROOT/$DB_PATH"
    fi

    if [[ -f "$DB_PATH" && "$DB_PATH" != "$ROOT_DB_PATH" ]]; then
      rm -f "$DB_PATH"
      echo "Deleted SQLite database: $DB_PATH"
    elif [[ ! -f "$DB_PATH" ]]; then
      echo "SQLite database not found at: $DB_PATH (continuing)"
    fi
  else
    echo "Non-SQLite or unresolved DB path; flushing database instead..."
    "$PYTHON_BIN" manage.py flush --no-input || true
  fi
fi

echo "Running makemigrations..."
"$PYTHON_BIN" manage.py makemigrations

echo "Running migrate..."
"$PYTHON_BIN" manage.py migrate

if [[ "$RUN_SEED" == "1" ]]; then
  echo "Running seed..."
  "$PYTHON_BIN" manage.py seed
fi

if [[ -n "${SED_EXPR:-}" && -n "${SED_FILE:-}" ]]; then
  if [[ -f "$SED_FILE" ]]; then
    echo "Applying sed to $SED_FILE"
    sed -i '' "$SED_EXPR" "$SED_FILE"
  else
    echo "Skipping sed: file '$SED_FILE' not found"
  fi
fi

echo "Starting Django server at http://${HOST}:${PORT}"
exec "$PYTHON_BIN" manage.py runserver "${HOST}:${PORT}"
