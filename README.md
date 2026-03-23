# QCC - Quality Control Center

QCC is a Flask + SQLite quality governance web application for BPO audit management, calibration governance, QA bandwidth control, and feedback tracking.

## Features
- Session-based authentication with Admin, QA, and Manager roles.
- Audit workflow with weighted scoring and a hard-stop at 90% QA utilization.
- Calibration variance monitoring with alerts above 10%.
- Feedback tracking with training/PIP escalation rules on repeated issues.
- Dashboard KPIs, Bootstrap UI, Chart.js visualizations, pagination, and CSV export.
- SQLite-backed deployment suitable for PythonAnywhere free tier.

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

## Seed sample data
```bash
python seed_data.py
```

## Default login
- Admin: `admin@qcc.local`
- Password: `admin123`

## PythonAnywhere deployment
1. Upload the repository to your PythonAnywhere home directory.
2. Create a Python 3.11 virtualenv and install dependencies with `pip install -r requirements.txt`.
3. Create a new manual web app configured for Flask.
4. Point the WSGI file to `wsgi_example.py` contents, or import `from app import app as application`.
5. Ensure the app directory is added to `sys.path` and reload the web app.
6. Use the Bash console to run `python seed_data.py` if you want demo data.
7. On free tier, keep SQLite in the project directory and avoid background workers or external services.
