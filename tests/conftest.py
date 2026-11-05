from __future__ import annotations

import pytest

import rfp.database.connection as connection_module
from rfp.database.repository import initialize_database


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(connection_module, "DB_PATH", tmp_path / "test_rfp.db")
    initialize_database()
    return connection_module.DB_PATH
