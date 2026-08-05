# OpsForge ERP v1.0.0

Released as a portfolio MVP on 5 August 2026.

OpsForge ERP v1.0.0 is the first complete, locally runnable demonstration of the project's scoped distribution workflows. It is fictional, non-commercial software and is not presented as a production deployment.

## Included

- Revocable token sessions, Argon2 password hashes, and admin/operator/support authorization.
- Product, warehouse, inventory balance, partner, user, and audit management.
- Atomic receipt, issue, adjustment, transfer, return, sales completion, and purchase receipt operations.
- Sales and purchase state machines with persisted idempotency protection.
- Product-specific reorder thresholds, expected purchase delivery dates, and a live operational dashboard.
- Atomic product CSV import plus product and inventory exports.
- Responsive React interface with permission-aware actions and support diagnostics.
- Deterministic local demo seed, four Alembic migrations, structured JSON logging, and request IDs.
- Pytest, Vitest, Playwright, static analysis, production build, Docker Compose, and GitHub Actions gates.
- Recruiter-focused README, architecture/data-model diagrams, test strategy, CSV guide, and seven-scenario support runbook.

## Release verification

- Empty Docker volume recreated successfully through `docker compose up -d --build`.
- PostgreSQL migrated from no schema to `0004_replenishment_fields (head)`.
- `alembic check` reported no pending upgrade operations.
- Seed produced 3 users, 6 products, 2 warehouses, 4 partners, 12 balances, 1 sales order, and 1 purchase order.
- 23 backend tests, 4 frontend tests, and the full six-step Playwright workflow passed.
- Ruff, formatting, mypy, ESLint, TypeScript, Vite production build, and npm dependency audit passed.
- Login, dashboard, inventory, expanded sales order, mobile navigation, permissions, and browser console were inspected in Chromium.

## Known limits

This release is local-Compose-only and does not include accounting, payroll, partial fulfillment, stock reservation, multi-tenancy, external identity, third-party integrations, a public hosted demo, or formal scale/security/compliance claims. See the README roadmap for planned improvements.

## Upgrade notes

This is the first portfolio release. Existing development databases upgrade normally through Alembic. For a deterministic local demonstration, run the seed after startup:

```bash
docker compose exec -T backend python -m app.db.seed
```
