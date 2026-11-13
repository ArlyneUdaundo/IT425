# Student Records Management

A student directory built with Django and PostgreSQL. It supports creating, viewing, searching, editing, and deleting student records, plus Django admin access.

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

Open <http://127.0.0.1:8000/> for the student directory or <http://127.0.0.1:8000/admin/> for the Django admin.

## Deploy to Render

The root `render.yaml` defines a free Render web service. Push this repository to GitHub, then in the [Render Dashboard](https://dashboard.render.com/blueprints) choose **New Blueprint Instance**, connect this repository, and apply the blueprint. Provide the `DATABASE_URL` of a PostgreSQL database when prompted. On startup, the app creates a dedicated `student_records_app` schema in that database, then runs migrations in that schema so its Django tables stay separate from tables in the database's default schema. Render will build the app, collect static files, and provide the live `.onrender.com` URL.

The blueprint generates a Django secret key and configures the production host and CSRF settings. After the first deployment, create an admin user from the web service's Shell using `python manage.py createsuperuser`.

## Student fields

Each record includes a unique student ID and email address, name, optional phone and address, date of birth, optional gender, course, and enrollment date. The directory can be searched by student ID, name, email, or course.
