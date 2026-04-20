from pathlib import Path
from typing import Sequence

import asyncpg


async def _applied_versions(conn: asyncpg.Connection) -> set[str]:
    rows: Sequence[asyncpg.Record] = await conn.fetch(
        "SELECT version FROM schema_migrations"
    )
    return {row["version"] for row in rows}


async def run_migrations(database_url: str, migrations_dir: Path) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        applied = await _applied_versions(conn)
        migration_files = sorted(migrations_dir.glob("*.sql"))

        for migration_file in migration_files:
            version = migration_file.name
            if version in applied:
                continue

            sql = migration_file.read_text(encoding="utf-8")
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations(version) VALUES($1)", version
            )
    finally:
        await conn.close()
