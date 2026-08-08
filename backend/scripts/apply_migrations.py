from __future__ import annotations

import os
from pathlib import Path

import psycopg


MIGRATION_LOCK_NAME = "guancha-schema-migrations-v1"


def main() -> None:
    dsn = os.getenv("GUANCHA_DATABASE_URL")
    if not dsn:
        raise SystemExit("GUANCHA_DATABASE_URL is required before applying migrations")

    repo_root = Path(__file__).resolve().parents[2]
    migrations_dir = repo_root / "supabase" / "migrations"
    migration_files = sorted(
        path
        for path in migrations_dir.glob("*.sql")
        if path.is_file() and not path.name.startswith(".")
    )
    if not migration_files:
        raise SystemExit(f"No migration files found in {migrations_dir}")

    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                create table if not exists guancha_schema_migrations (
                    filename text primary key,
                    applied_at timestamptz not null default now()
                )
                """
            )
            cursor.execute("select pg_advisory_lock(hashtext(%s))", (MIGRATION_LOCK_NAME,))

        try:
            with connection.cursor() as cursor:
                cursor.execute("select filename from guancha_schema_migrations")
                applied = {row[0] for row in cursor.fetchall()}

            for migration_path in migration_files:
                if migration_path.name in applied:
                    print(f"[migration] already applied: {migration_path.name}")
                    continue

                sql = migration_path.read_text(encoding="utf-8")
                print(f"[migration] applying: {migration_path.name}")
                with connection.transaction():
                    with connection.cursor() as cursor:
                        cursor.execute(sql)
                        while cursor.nextset():
                            pass
                        cursor.execute(
                            "insert into guancha_schema_migrations (filename) values (%s)",
                            (migration_path.name,),
                        )
                print(f"[migration] applied: {migration_path.name}")
        finally:
            with connection.cursor() as cursor:
                cursor.execute("select pg_advisory_unlock(hashtext(%s))", (MIGRATION_LOCK_NAME,))


if __name__ == "__main__":
    main()
