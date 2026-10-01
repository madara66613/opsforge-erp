# OpsForge ERP

[![CI](https://github.com/madara66613/opsforge-erp/actions/workflows/ci.yml/badge.svg)](https://github.com/madara66613/opsforge-erp/actions/workflows/ci.yml)

An inventory and order-management application for a small distributor workflow. The FastAPI backend handles warehouse balances, sales, purchasing, permissions, and audit records; the React interface exposes those operations. All seeded business data is fictional.

![OpsForge dashboard](docs/screenshots/dashboard.png)

## Functionality

- Products, partners, warehouses, stock balances, and movement history.
- Receipts, issues, adjustments, transfers, returns, and an admin-only negative-stock override.
- Sales: `draft → confirmed → processing → completed`, with cancellation before completion.
- Purchasing: `draft → ordered → received`, with expected-delivery dates.
- Admin, operator, and support roles enforced by the API; revocable bearer sessions and Argon2 password hashes.
- Product CSV import with whole-file validation; product and inventory exports. See the [CSV guide](docs/csv-guide.md) and [sample file](samples/products.csv).
- Dashboard totals, low-stock balances, request IDs, JSON access logs, and health/readiness/version endpoints.

## Transaction boundaries

Order completion and purchase receipt lock the affected order and inventory rows. Stock balances, movement records, order state, idempotency records, and the success audit event are committed together. Replaying an operation with its persisted idempotency key does not repeat stock movements; reusing the key for another resource is rejected. Failed domain operations roll back business changes and write a separate failure audit event.

The backend is a modular monolith with API routes, domain services, and SQLAlchemy models. Alembic manages the PostgreSQL schema. See [architecture](docs/architecture.md), [data model](docs/data-model.md), and [business rules](docs/business-rules.md).

## Stack

Python 3.12+ · FastAPI · SQLAlchemy 2 · PostgreSQL 17 · Alembic · React · TypeScript · Docker Compose

Quality checks use pytest, Ruff, mypy, Vitest, ESLint, and Playwright.

## Quick start

Requires a running Docker engine with Compose.

```bash
git clone https://github.com/madara66613/opsforge-erp.git
cd opsforge-erp
cp .env.example .env
docker compose up --detach --build --wait
docker compose exec -T backend python -m app.db.seed
```

Open the [application](http://localhost:3000) or [API documentation](http://localhost:8000/docs). Startup applies migrations; PostgreSQL data persists in the `opsforge_db` volume. The seed can be rerun and is restricted to local/test environments.

| Role | Email | Local demo password |
| --- | --- | --- |
| Admin | `admin@demo.opsforge.dev` | `AdminDemo!2026` |
| Operator | `operator@demo.opsforge.dev` | `OperatorDemo!2026` |
| Support | `support@demo.opsforge.dev` | `SupportDemo!2026` |

For host development, use Python 3.12+ and Node.js 22+:

```bash
make bootstrap
make check
```

## Tests and diagnostics

`make check` runs backend lint, formatting, type checks and pytest, then frontend lint, type checks, Vitest and a build. The API/service tests use SQLite fixtures; they cover rollback, permissions, idempotency, audit records, and CSV atomicity. CI additionally applies migrations to PostgreSQL and checks schema drift. The fixture tests do not verify concurrent PostgreSQL locking.

With a healthy, seeded Compose stack:

```bash
npm --prefix frontend run test:e2e
```

The browser test creates a product, receives 12 units, completes a two-unit sale, verifies the remaining ten units, and checks the audit log. See the [test strategy](docs/test-strategy.md).

`/health` checks the API process, `/ready` checks the database, and `/version` returns build metadata. The [support runbook](docs/support-runbook.md) covers diagnosis and recovery; [authorization](docs/authorization.md) describes role permissions.

## Limits

The maintained runtime is local Docker Compose. Orders use PLN and have no stock reservation, partial fulfillment, invoicing, or payment processing. There is no multi-tenancy or external identity integration. Browser coverage targets Chromium, and concurrent stock operations have not been load-tested.

[MIT license](LICENSE)
