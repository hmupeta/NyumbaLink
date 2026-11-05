# NyumbaLink

Find your place. Connect your world.

## Quick start

    docker compose up -d
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt
    cp .env.example .env
    python manage.py migrate
    python manage.py seed_locations
    python manage.py createsuperuser
    python manage.py runserver

Open http://127.0.0.1:8000/api/docs/ and http://127.0.0.1:8000/health/

## Layout

    config/settings/{base,dev,prod}.py   split settings
    apps/accounts/                       custom User, UUID pk, email login
    apps/locations/                      Province > District > Locality > Neighbourhood
    apps/core/                           shared models, health check

## Conventions

- All primary keys are UUIDs.
- Email is the login identifier and is unique case-insensitively.
- Nothing is deleted that has financial or audit relevance.
- Credentials live in .env, never in settings.
