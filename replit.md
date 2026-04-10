# Terrain de Proximité de Smimou

A web-based reservation management system for a community sports field in Smimou, Essaouira, Morocco.

## Project Structure

- `app.py` — Main Flask application with all routes, models, and business logic
- `translations.py` — Multi-language support (French, English, Arabic)
- `main.py` — Simple entry point (not used by Flask directly)
- `templates/` — Jinja2 HTML templates (moved from root during Replit setup)
  - `base.html` — Master layout
  - `index.html` — Landing page
  - `planning.html` — Calendar/schedule view
  - `reservation.html` — Public booking form
  - `admin_login.html` — Admin login
  - `admin_dashboard.html` — Admin panel
  - `admin_new_reservation.html` — Admin booking form
  - `admin_settings.html` — Admin time slot configuration

## Tech Stack

- **Backend:** Flask (Python 3.12)
- **Database:** SQLite via Flask-SQLAlchemy (file: `terrain.db`, created at runtime)
- **Frontend:** Bootstrap 5.3.2 with Jinja2 templates
- **Production server:** Gunicorn

## Running the App

The app runs on port 5000 via the "Start application" workflow using:
```
python -c 'from app import init_db; init_db()' && gunicorn --bind 0.0.0.0:5000 --reuse-port --reload app:app
```
The database is initialized before gunicorn starts, creating tables and seeding sample data on the first run.

## Deployment

Configured for autoscale deployment using Gunicorn:
```
gunicorn --bind=0.0.0.0:5000 --reuse-port app:app
```

## Default Admin Credentials

- Username: `admin`
- Password: `berserker2005@`

## Features

- Public booking system with conflict detection
- Admin dashboard with filtering and status management
- Configurable time slots
- Multilingual support (French, English, Arabic) with RTL for Arabic
- Auto-initialized sample data on first run
