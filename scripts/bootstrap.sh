#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if [ ! -f "$project_root/.env" ]; then
  cp "$project_root/.env.example" "$project_root/.env"
  printf '%s\n' "Created .env from .env.example (local-demo values only)."
fi

python3 -m venv "$project_root/.venv"
"$project_root/.venv/bin/python" -m pip install --upgrade pip
"$project_root/.venv/bin/python" -m pip install -e "$project_root/backend[dev]"
npm --prefix "$project_root/frontend" install

printf '%s\n' "Bootstrap complete. Run 'make check' or 'docker compose up --build'."

