import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """Point db.DB_PATH at a tmp file, re-init schema, yield the reloaded module."""
    db_path = tmp_path / "test_bot.db"
    monkeypatch.setenv("BOT_DB_PATH", str(db_path))
    # Reimport so DB_PATH module-level constant picks up the env var.
    import db as db_module  # noqa: WPS433

    importlib.reload(db_module)
    db_module.init_db()
    yield db_module
