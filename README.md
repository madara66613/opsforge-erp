# OpsForge ERP

OpsForge ERP is a portfolio-grade enterprise resource planning system for a fictional small distributor. It demonstrates the work behind reliable operational software: explicit inventory rules, transactional order workflows, role-based access, auditability, support diagnostics, automated tests, and containerized delivery.

> Portfolio project only. OpsForge ERP is fictional, non-commercial software and is not intended for production business use.

## Why this project exists

The repository is designed to be useful in interviews for ERP consulting, application support, Python backend, QA, SQL support, and junior DevOps roles. It favors a small, understandable architecture over a large collection of shallow features.

## Foundation status

Milestone 0 establishes:

- FastAPI application boundaries and `/health`, `/ready`, and `/version` probes;
- structured JSON request logging with request IDs;
- PostgreSQL and Alembic wiring;
- React, TypeScript, Vite, Vitest, and a production Nginx image;
- one-command Docker Compose topology with health checks and persistent database storage;
- backend and frontend quality gates in GitHub Actions.

The domain workflows and final ERP interface are implemented in subsequent reviewable milestones. See [the delivery checklist](docs/milestones.md).

Authentication is already implemented with Argon2 password hashes, revocable opaque bearer sessions, and backend-enforced permissions. See [the authorization model](docs/authorization.md).

The inventory domain includes searchable products and warehouses, one balance per product/warehouse pair, and immutable receipt, issue, transfer, return, and adjustment movements. Stock-changing operations lock balances and commit atomically. See [the business rules](docs/business-rules.md) and [data model](docs/data-model.md).

## Quick start

Prerequisites: Docker with Compose.

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- web application: <http://localhost:3000>
- API documentation: <http://localhost:8000/docs>
- readiness probe: <http://localhost:8000/ready>

Seed the deterministic local demo users:

```bash
docker compose exec backend python -m app.db.seed
```

| Role | Email | Local-only password |
| --- | --- | --- |
| Admin | `admin@demo.opsforge.dev` | `AdminDemo!2026` |
| Operator | `operator@demo.opsforge.dev` | `OperatorDemo!2026` |
| Support | `support@demo.opsforge.dev` | `SupportDemo!2026` |

These credentials are fictional and intentionally limited to local seeded environments.

Stop the stack without deleting persisted data:

```bash
docker compose down
```

## Local development checks

Python 3.12+ and Node.js 22+ are required outside Docker.

```bash
make bootstrap
make check
```

## Architecture

OpsForge ERP is a modular monolith: a React SPA calls versioned FastAPI routes; route handlers delegate business decisions to a transactional service layer; SQLAlchemy models and PostgreSQL constraints protect persistence invariants. Read [the architecture notes](docs/architecture.md) for boundaries and operational principles.

## Repository layout

```text
backend/       FastAPI, SQLAlchemy, Alembic, and pytest
frontend/      React, TypeScript, Vite, Vitest, and Nginx
docs/          Architecture, business, support, and testing documentation
scripts/       Reproducible local workflows
compose.yaml   PostgreSQL + backend + frontend topology
```

## License

[MIT](LICENSE)
