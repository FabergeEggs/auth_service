from pathlib import Path


def test_migration_files_exist_and_ordered():
    migrations_dir = Path(__file__).resolve().parents[2] / "migrations"
    files = sorted(p.name for p in migrations_dir.glob("*.sql"))
    assert files == [
        "0001_init_auth_schema.sql",
        "0002_add_outbox_events.sql",
    ]


def test_initial_migration_contains_core_tables():
    migration = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "0001_init_auth_schema.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS auth_users" in migration
    assert "CREATE TABLE IF NOT EXISTS auth_sessions" in migration


def test_outbox_migration_contains_outbox_table():
    migration = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "0002_add_outbox_events.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS auth_outbox_events" in migration
