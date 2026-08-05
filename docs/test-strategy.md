# Test strategy

OpsForge ERP uses a risk-based test pyramid. The highest priority is preventing unauthorized writes, partial inventory changes, duplicate order processing, and schema drift.

## Quality gates

`make check` is the local and CI-aligned gate. It runs:

1. Ruff lint and formatting verification;
2. mypy over the FastAPI application;
3. pytest backend suite;
4. ESLint and TypeScript checks;
5. Vitest interaction and permission tests;
6. Vite production build.

Alembic is additionally validated against a fresh PostgreSQL database with `alembic upgrade head` followed by `alembic check`.

## Coverage by risk

| Risk | Primary automated evidence |
| --- | --- |
| Authentication bypass or leaked raw token | login/logout/session hashing tests; permission endpoint tests |
| Unauthorized business mutation | admin/operator/support matrix tests on users, inventory, partners, orders, and CSV |
| Negative or inconsistent inventory | movement rule tests; row-locking service paths; rollback assertions |
| Partial order processing | failed sales rollback test; purchase/sales atomic transaction tests |
| Duplicate stock deduction | persisted idempotency replay/conflict tests |
| Invalid master data | Pydantic validation, unique SKU/code conflict tests, database checks |
| Partial CSV import | valid/invalid/duplicate/header tests with database row-count assertions |
| Schema drift | fresh PostgreSQL migration and `alembic check` |
| Permission-confusing UI | frontend role matrix tests and real-browser role walkthroughs |
| Broken recruiter demo | Playwright E2E workflow against the Compose stack |

## Backend tests

The pytest suite uses an isolated in-memory SQLite database per test for fast service and API feedback. It covers authentication, RBAC, catalog validation, audit events, inventory movement rules, sales and purchase state machines, rollback, idempotency, CSV atomicity, and system probes.

SQLite does not replace PostgreSQL verification. Migrations, row-lock syntax, constraints, seed behavior, and representative API calls are separately executed against the Compose PostgreSQL service.

## Frontend tests

Vitest and Testing Library exercise behavior rather than static rendering: demo-role selection, API login, dashboard data loading, and visibility of permission-gated navigation. The frontend typechecker ensures API contracts are represented consistently across pages.

## End-to-end test

The Playwright flow runs against the full Docker Compose application and covers the required recruiter workflow:

1. log in as an admin;
2. create a uniquely identified product through the UI;
3. receive initial stock;
4. create and complete a sales order;
5. verify the remaining balance;
6. inspect the resulting successful audit event.

Run it only after the stack is healthy and seeded:

```bash
docker compose up -d --build
docker compose exec -T backend python -m app.db.seed
npm --prefix frontend run test:e2e
```

The scenario uses a unique SKU per run so it can be repeated without deleting database state. It does not use an admin negative-stock override.

## Determinism and data

- Unit/API tests create isolated records and never depend on execution order.
- Seed IDs, users, warehouses, products, balances, and opening movements are deterministic and idempotent.
- Decimal values are asserted as decimals, not binary floats.
- Time-sensitive session tests use broad valid/expired boundaries rather than exact elapsed milliseconds.
- E2E locators use accessible roles, labels, and visible business identifiers.

## Manual and visual checks

Before a portfolio release, inspect login, dashboard, tabular modules, forms, order details, system status, admin pages, and mobile navigation in Chromium. Confirm there are no browser console errors, secrets in logs/audit records, broken README links, or misleading claims.

## Known test limitations

- The portfolio suite does not load-test concurrency or claim enterprise-scale performance.
- Browser coverage focuses on Chromium; cross-browser compatibility is not claimed.
- No external identity provider, email delivery, cloud storage, or third-party API is in MVP scope.
