#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

"$project_root/.venv/bin/ruff" check "$project_root/backend"
"$project_root/.venv/bin/ruff" format --check "$project_root/backend"
"$project_root/.venv/bin/mypy" "$project_root/backend/app"
"$project_root/.venv/bin/pytest" "$project_root/backend/tests"
npm --prefix "$project_root/frontend" run lint
npm --prefix "$project_root/frontend" run typecheck
npm --prefix "$project_root/frontend" run test -- --run
npm --prefix "$project_root/frontend" run build

