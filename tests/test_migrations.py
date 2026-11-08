from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_review_migration_round_trip(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_engine(url)
    assert {
        "review_cases",
        "review_proposals",
        "merchant_approvals",
        "review_outbox",
        "review_audit",
    } <= set(inspect(engine).get_table_names())
    command.check(config)
    command.downgrade(config, "base")
    assert not {name for name in inspect(engine).get_table_names() if name.startswith("review_")}
    engine.dispose()
