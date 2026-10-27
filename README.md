# BusinessOS

Django business-management platform: orders, inventory, customers, expenses, payments, invoices,
analytics, AI sales forecast, team roles and a JWT REST API.

## Quick start (local, SQLite)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo          # demo workspace + one user per role
python manage.py runserver
```
Open http://127.0.0.1:8000 and sign in with `owner / Owner@12345` (also `admin / Admin@12345`,
`manager / Manager@12345`, `staff / Staff@12345`, `accountant / Accountant@12345`).

## Forgot password
Login page -> **Forgot password?** -> enter email -> open the emailed link -> choose a new password.
In development the email is printed in the terminal (console backend). For real emails set `EMAIL_HOST`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (and `DEFAULT_FROM_EMAIL`) in `.env`. Links expire after
`PASSWORD_RESET_TIMEOUT` seconds (default 1 hour).

## Docker (MySQL + gunicorn)
```bash
cp .env.example .env     # set SECRET_KEY, DB_PASSWORD, DB_ROOT_PASSWORD, ALLOWED_HOSTS
docker compose up -d --build
docker compose exec web python manage.py createsuperuser   # optional
```
Services: `db` (MySQL 8.4), `web` (gunicorn + WhiteNoise static), `scheduler` (daily AI forecast refresh).
Health check: `GET /health/`.

## Front-end
One design system for every app:
- `static/css/master.css` - tokens, layout shell, sidebar, forms, tables, cards, badges, responsive rules
- `static/js/master.js` - hamburger drawer, toasts, confirm dialogs, password toggle
- `templates/base.html` (app), `base_auth.html` (login/signup), `base_public.html` (landing)
- Mobile (<= 960px): sidebar becomes a hamburger drawer; tables turn into cards.

## REST API
Base `/api/v1/` - Swagger at `/api/v1/docs/`, ReDoc at `/api/v1/redoc/`, schema at `/api/v1/schema/`.
```bash
curl -X POST localhost:8000/api/v1/token/ -H 'Content-Type: application/json' \
     -d '{"username":"owner","password":"Owner@12345"}'          # username or email
curl localhost:8000/api/v1/dashboard/ -H "Authorization: Bearer <access>"
```
Resources: `Product, Customer, Order, Inventory, Expense, Payment, Invoice, Notification, Account,
Organisation`, plus `dashboard/`, `profile/`, `forecasts/`, `forecasts/generate/`,
`Order/{id}/status/`, `Notification/mark-all-read/`. See `api_test.http` for examples.
Orders take `items_input: [{"product": id, "quantity": n}]`; stock, ledger, invoice/payment sync are automatic.

## CI/CD (GitHub Actions)
- `ci.yml`: lint, migrations check, tests on SQLite and MySQL, Docker build + smoke test.
- `cd.yml`: builds and pushes `ghcr.io/<owner>/<repo>` on main/tags; optional SSH deploy when the repo
  variable `DEPLOY_ENABLED=true` and secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH` exist.

## Useful commands
`make test` · `make seed` · `make forecast` · `make schema` · `make docker-up`

## Roles
Owner and Admin manage everything (Admin cannot touch Owners). Manager: operations + reports. Staff: orders,
customers, stock. Accountant: expenses, payments, invoices. Rules live in `common/roles.py`.
