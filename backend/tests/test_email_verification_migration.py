from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_existing_accounts_are_verified_by_migration(tmp_path, monkeypatch):
    backend = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    command.upgrade(config, "33bbd8f9f146")

    engine = create_engine(database_url)
    with engine.begin() as db:
        db.execute(
            text("INSERT INTO users (id, email, password_hash, time_zone, created_at) "
                 "VALUES (:id, :email, :password_hash, :time_zone, :created_at)"),
            {
                "id": "old-user",
                "email": "old@example.com",
                "password_hash": "legacy-test-hash",
                "time_zone": "Asia/Manila",
                "created_at": "2026-01-01 00:00:00",
            },
        )

    command.upgrade(config, "head")
    with engine.connect() as db:
        row = db.execute(text("SELECT email_verified_at, email_otp_attempts, theme FROM users WHERE id = 'old-user'")).one()
        assert row.email_verified_at is not None
        assert row.email_otp_attempts == 0
        assert row.theme == "orange-yellow"
    engine.dispose()
