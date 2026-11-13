import os

import psycopg


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set before preparing the database.")

    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "CREATE SCHEMA IF NOT EXISTS student_records_app "
            "AUTHORIZATION CURRENT_USER"
        )


if __name__ == "__main__":
    main()
