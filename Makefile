.PHONY: bootstrap check up down logs seed

bootstrap:
	./scripts/bootstrap.sh

check:
	./scripts/check.sh

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f backend frontend db

seed:
	docker compose exec backend python -m app.db.seed

