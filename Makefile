.PHONY: install run test migrate seed forecast lint docker-up docker-down docker-logs schema

install:        ## install dev dependencies
	pip install -r requirements-dev.txt
run:            ## start the dev server
	python manage.py migrate && python manage.py runserver
test:
	python -m pytest
migrate:
	python manage.py migrate
seed:           ## demo org + users (owner / Owner@12345 ...)
	python manage.py seed_demo
forecast:
	python manage.py generate_forecasts
lint:
	ruff check . --select E9,F63,F7,F82,F401 --exclude migrations
schema:         ## export the OpenAPI schema
	python manage.py spectacular --file openapi.yml
docker-up:
	docker compose up -d --build
docker-down:
	docker compose down
docker-logs:
	docker compose logs -f web
