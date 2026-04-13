# SPMS Project

A Student/Project Management System (SPMS) originally built with Python and MySQL. This repository has been restructured into a clean Flask-style layout with a modern entrypoint, environment-based configuration, and deployment-ready files.

## Project structure

- `app/` - Flask application package and routes
- `templates/` - HTML templates for the web interface
- `static/` - CSS, JS, and static assets
- `database/` - database connection helpers
- `config/` - environment-based application configuration
- `legacy/` - original Tkinter/MySQL code preserved for reference
- `app.py` - Flask application entrypoint
- `requirements.txt` - Python dependencies
- `.env.example` - sample environment variables
- `Procfile` - deployment entrypoint for platforms like Heroku

## Setup

1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and update values:
   ```bash
   copy .env.example .env
   ```

4. Run the app:
   ```bash
   python app.py
   ```

## Environment variables

- `SECRET_KEY` - Flask secret key
- `MYSQL_HOST` - MySQL hostname
- `MYSQL_USER` - MySQL username
- `MYSQL_PASSWORD` - MySQL password
- `MYSQL_DB` - MySQL database name
- `MYSQL_PORT` - MySQL port

## Deployment

Use the included `Procfile` for deployment on platforms that support Gunicorn:

```bash
web: gunicorn app:app
```

## Notes

- The current structure includes the original GUI version in `legacy/`.
- The Flask scaffold is ready for web-based feature migration.
