# Educate Student Record Management System

A Django and PostgreSQL academic records app with separate registrar, instructor, and student portals. Registrars manage the roster and course catalog, instructors view their assigned subject rosters, and students see their own linked records and subjects.

## Requirements

- Python 3.10+
- PostgreSQL 13+

## Setup

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create a PostgreSQL database:

   ```sql
   CREATE DATABASE student_records;
   ```

4. Configure the database and Django settings. Copy `.env.example` to `.env` and set the values for your PostgreSQL server. The application reads environment variables directly; PowerShell does not load `.env` automatically. Set them in the shell before starting the server, or use your preferred environment-file loader:

   ```powershell
   $env:PGDATABASE = "student_records"
   $env:PGUSER = "postgres"
   $env:PGPASSWORD = "your-postgres-password"
   $env:PGHOST = "127.0.0.1"
   $env:PGPORT = "5432"
   $env:DJANGO_SECRET_KEY = "use-a-long-random-secret"
   ```

5. Apply migrations and create an admin account:

   ```powershell
   py manage.py migrate
   py manage.py createsuperuser
   ```

6. Start the development server:

   ```powershell
   py manage.py runserver
   ```

Open <http://127.0.0.1:8000/> to sign in. The portal shown after sign-in depends on the account's role. Django admin is at <http://127.0.0.1:8000/admin/>.

## Roles and sample academic data

- **Registrar:** manage student records, courses, and subjects, and assign instructors to subjects.
- **Instructor:** view assigned subjects and the corresponding course rosters.
- **Student:** create an account using the student ID and email already on their registrar-created record, then view that record and the subjects in their course.
- Registrars can create registrar and instructor accounts from the registrar dashboard. Public sign-up is limited to students; staff roles cannot be selected during student registration.

To create the requested sample roster locally, run:

```powershell
py manage.py seed_demo_data
```

This idempotently creates 1 registrar, 2 instructors, 10 students, 10 courses, and 10 sample subjects per course (100 total). New accounts get unique randomly generated passwords printed once by the command. Save them securely and change them after first sign-in. Existing passwords are never reset by rerunning the command. To set a shared initial password for newly created demo accounts instead, pass `--password "your-temporary-password"` and change the accounts individually afterward.

## Deploy to Render

The root `render.yaml` defines a free Render web service. Push this repository to GitHub, then in the [Render Dashboard](https://dashboard.render.com/blueprints) choose **New Blueprint Instance**, connect this repository, and apply the blueprint. Provide the `DATABASE_URL` of a PostgreSQL database when prompted. On startup, the app creates a dedicated `student_records_app` schema in that database, then runs migrations in that schema so its Django tables stay separate from tables in the database's default schema. Render will build the app, collect static files, and provide the live `.onrender.com` URL.

The blueprint generates a Django secret key and configures the production host and CSRF settings. After deploying, run `python manage.py seed_demo_data` to provision the sample registrar, instructors, students, courses, and subjects. Render's Shell is available only for paid web services; for a Free web service, run the command locally against the database's **External Database URL** from the Render dashboard:

```powershell
$env:DATABASE_URL = "<External Database URL from Render>"
py manage.py seed_demo_data
Remove-Item Env:DATABASE_URL
```

Run this from the project directory with the dependencies installed. Do not share or commit the database URL. Store the generated initial passwords securely; the command prints passwords only for accounts it creates. Alternatively create an administrator with `python manage.py createsuperuser`; Django superusers receive registrar access.

## Student fields

Each student record includes a unique student ID and email address, name, optional phone and address, date of birth, optional gender, course, enrollment date, and an optional linked portal account. Courses group students and contain subjects; subjects can be assigned to instructors.
