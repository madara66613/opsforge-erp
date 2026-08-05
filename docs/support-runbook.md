# Support runbook

This runbook covers the local portfolio environment. It demonstrates a safe diagnostic process; it does not describe incidents from a real company or claim production operations.

Run commands from the repository root. Never paste bearer tokens, passwords, `.env` contents, or full database dumps into tickets. Capture the timestamp, affected role, endpoint, HTTP status, and `X-Request-ID` response header before changing state.

## First response

1. Confirm scope: one user, one browser, one workflow, or the full stack.
2. Capture evidence with `docker compose ps`, the failing command, timestamp, HTTP status, and request ID.
3. Check `GET /health` before `GET /ready`; this separates process health from database dependency health.
4. Review a narrow log window: `docker compose logs --since=10m backend db frontend`.
5. Prefer reversible recovery. Do not delete the named PostgreSQL volume as a troubleshooting shortcut.

## 1. Backend cannot connect to PostgreSQL

**Symptoms:** backend is restarting or unhealthy; `/health` may work briefly while `/ready` returns `503`; backend logs contain a database connection error.

**Likely causes:** database container is not ready, credentials or database name differ between services, port conflict, or the database volume cannot start.

**Diagnose:**

```bash
docker compose ps
docker compose logs --since=10m db backend
docker compose exec -T db pg_isready -U opsforge -d opsforge
docker compose exec -T backend python -c "from app.db.session import engine; from sqlalchemy import text; print(engine.connect().execute(text('SELECT 1')).scalar())"
```

**Safe resolution:** compare variable names with `.env.example`; restart only the affected services with `docker compose up -d db backend`; wait for the database health check. If credentials changed after a volume was created, restore the original local values or create an explicitly named new development database rather than deleting data.

**Escalate when:** PostgreSQL reports storage corruption, repeated crash recovery, permission errors on its data directory, or the failure persists with matching configuration and a healthy `pg_isready` result.

## 2. Database migration failed

**Symptoms:** backend startup stops during `alembic upgrade head`; a revision is missing; PostgreSQL reports a constraint or DDL error.

**Likely causes:** code and database revision are out of sync, a branch omitted a migration, or existing data violates a new constraint.

**Diagnose:**

```bash
docker compose exec -T backend alembic current
docker compose exec -T backend alembic heads
docker compose exec -T backend alembic history --verbose
docker compose logs --since=10m backend db
```

**Safe resolution:** keep the full traceback and failing revision; verify that the expected migration file exists; reproduce on a newly created, explicitly named temporary database; correct the migration or data precondition in code. Do not stamp a failed database to `head`, edit Alembic history, or run ad-hoc destructive DDL.

**Escalate when:** a migration partially committed, rollback would remove user-created data, more than one head exists unexpectedly, or a production-like backup/restore decision is required.

## 3. Frontend cannot reach the API

**Symptoms:** pages show “Unable to load data,” login reports a network error, or browser developer tools show `502`, CORS, or connection-refused errors.

**Likely causes:** backend is unhealthy, Nginx proxy target is unavailable, an unsupported origin is configured, or the browser has stale assets.

**Diagnose:**

```bash
curl -i http://localhost:3000/health
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
docker compose logs --since=10m frontend backend
```

**Safe resolution:** restore backend readiness first; rebuild only the changed images with `docker compose up -d --build backend frontend`; hard-refresh the browser. For direct Vite development, confirm its `/api`, `/health`, `/ready`, and `/version` proxy targets in `frontend/vite.config.ts`.

**Escalate when:** direct backend requests work but proxied requests consistently fail, CORS differs from `.env.example`, or request IDs show the API completed successfully while the browser did not receive the response.

## 4. Login fails for all users

**Symptoms:** all three documented demo accounts return `401`, including after reseeding; no user can reach the workspace.

**Likely causes:** demo data was not seeded, the environment blocks demo seeding, users are inactive, clock/session settings are invalid, or the database is not the one expected.

**Diagnose:**

```bash
docker compose exec -T backend python -m app.db.seed
docker compose exec -T db psql -U opsforge -d opsforge -c "SELECT email, role, is_active FROM users ORDER BY email;"
docker compose logs --since=10m backend
curl -i http://localhost:8000/ready
```

Check the audit log for `auth.login` failures, but never log or compare plaintext passwords.

**Safe resolution:** seed only when `OPSFORGE_ENVIRONMENT` is `local` or `test`; confirm the exact local-only credentials in the README; reactivate or reset an account only through an authorized admin workflow. Avoid direct password updates because stored values must be Argon2 hashes.

**Escalate when:** valid active accounts still fail after readiness and seed checks, hashing raises runtime errors, or session timestamps are inconsistent with the host clock.

## 5. Inventory operation returns a conflict

**Symptoms:** a movement, sales completion, or purchase receipt returns `409`; the UI reports insufficient stock, invalid status, inactive master data, or duplicate idempotency use.

**Likely causes:** insufficient source quantity, incompatible order state, inactive product/partner/warehouse, same transfer source and destination, or a reused idempotency key for a different resource.

**Diagnose:**

```bash
docker compose logs --since=10m backend
docker compose exec -T db psql -U opsforge -d opsforge -c "SELECT p.sku, w.code, b.quantity FROM inventory_balances b JOIN products p ON p.id=b.product_id JOIN warehouses w ON w.id=b.warehouse_id ORDER BY p.sku,w.code;"
```

Use the response request ID to locate the matching failure audit entry and inspect its `reason`. Confirm that no balance or status partially changed.

**Safe resolution:** correct the source data or workflow state and submit a new valid operation. Replaying the exact same completion/receipt with the same key is safe. Negative inventory override is admin-only and should be an explicit business decision, not a routine recovery.

**Escalate when:** balances changed despite a failed response, duplicate movements share one order reference, the same idempotency key produced different effects, or database constraints and the movement ledger disagree.

## 6. CSV or demo seed import fails

**Symptoms:** CSV import returns `422` or `409`; the UI identifies a row and field; seed rejects the environment or stops with a constraint error.

**Likely causes:** incorrect header order, non-UTF-8 input, invalid decimal/boolean values, duplicate SKU, a file larger than 2 MB, or seeding outside `local`/`test`.

**Diagnose:**

```bash
head -n 5 samples/products.csv
file -I samples/products.csv
docker compose logs --since=10m backend
docker compose exec -T backend python -m app.db.seed
```

Expected product headers are documented in [the CSV guide](csv-guide.md). The `csv.products.import` audit event records row and error counts without storing uploaded content.

**Safe resolution:** copy the sample header exactly, correct every reported row, save as UTF-8, and retry. The importer validates the complete file before writing, so invalid input does not require cleanup. Seed is deterministic and may be rerun in local/test environments.

**Escalate when:** any product exists after a rejected import, a valid sample fails unchanged, seed changes existing business transactions, or an integrity conflict repeats without concurrent requests.

## 7. Readiness reports an unhealthy dependency

**Symptoms:** `/health` returns `200` but `/ready` returns `503`, and Compose marks the backend or frontend unhealthy.

**Likely causes:** PostgreSQL is unavailable, credentials are invalid, connection slots are exhausted, or a network/storage problem prevents queries.

**Diagnose:**

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
docker compose ps
docker compose logs --since=10m backend db
docker compose exec -T db pg_isready -U opsforge -d opsforge
```

**Safe resolution:** resolve database health first, then allow the backend health check to recover naturally or restart only the backend. Do not change `/ready` to return success while dependencies are unavailable.

**Escalate when:** `pg_isready` succeeds but `SELECT 1` from the backend fails, failures recur under normal local load, or PostgreSQL reports exhausted connections or storage errors.

## Evidence package for escalation

Include the observed/expected behavior, minimal reproduction, role, timestamp and timezone, endpoint/status, request ID, `docker compose ps`, narrow sanitized logs, current Alembic revision, and whether the issue reproduces after a clean browser session. Exclude secrets and personal data.
