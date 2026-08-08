from __future__ import annotations

import asyncio
import os
from pathlib import Path

import psycopg


# A fixed application-scoped PostgreSQL advisory lock prevents two CloudBase
# instances from applying the same migration concurrently during a rollout.
_MIGRATION_LOCK_ID = 681_240_517_202_608


def _migration_files() -> list[Path]:
    repository_root = Path(__file__).resolve().parents[2]
    migration_dir = repository_root / "supabase" / "migrations"
    files = sorted(path for path in migration_dir.glob("*.sql") if path.is_file())
    if not files:
        raise RuntimeError(f"No SQL migrations found in {migration_dir}")
    return files


async def migrate() -> None:
    database_url = os.getenv("GUANCHA_DATABASE_URL")
    if not database_url:
        raise RuntimeError("GUANCHA_DATABASE_URL is required before starting Guancha")

    connection = await psycopg.AsyncConnection.connect(
        database_url,
        autocommit=True,
        connect_timeout=15,
    )
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "select pg_advisory_lock(%s)",
                (_MIGRATION_LOCK_ID,),
            )
            try:
                await cursor.execute(
                    """
                    create table if not exists guancha_schema_migrations (
                        filename text primary key,
                        applied_at timestamptz not null default now()
                    )
                    """
                )

                for migration_path in _migration_files():
                    await cursor.execute(
                        "select 1 from guancha_schema_migrations where filename = %s",
                        (migration_path.name,),
                    )
                    if await cursor.fetchone() is not None:
                        print(f"[migration] already applied: {migration_path.name}", flush=True)
                        continue

                    migration_sql = migration_path.read_text(encoding="utf-8")
                    print(f"[migration] applying: {migration_path.name}", flush=True)
                    async with connection.transaction():
                        async with connection.cursor() as migration_cursor:
                            # The migration files intentionally contain multiple SQL
                            # commands (and one PL/pgSQL function body). prepare=False
                            # keeps them on PostgreSQL's simple-query path as one
                            # transaction without unsafe statement splitting.
                            await migration_cursor.execute(migration_sql, prepare=False)
                            await migration_cursor.execute(
                                "insert into guancha_schema_migrations (filename) values (%s)",
                                (migration_path.name,),
                            )
                    print(f"[migration] applied: {migration_path.name}", flush=True)
            finally:
                await cursor.execute(
                    "select pg_advisory_unlock(%s)",
                    (_MIGRATION_LOCK_ID,),
                )
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(migrate())
