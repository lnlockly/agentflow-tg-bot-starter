"""Verify only OWNER_TG_ID can pass the admin gate."""
from __future__ import annotations

import importlib

OWNER = 1361064246
INTRUDER = 9999999


def _reload_admin(monkeypatch, owner_value: str):
    monkeypatch.setenv("OWNER_TG_ID", owner_value)
    import admin as admin_module  # noqa: WPS433

    importlib.reload(admin_module)
    return admin_module


def test_is_owner_true_for_creator(monkeypatch):
    admin = _reload_admin(monkeypatch, str(OWNER))
    assert admin.is_owner(OWNER) is True


def test_is_owner_false_for_random_user(monkeypatch):
    admin = _reload_admin(monkeypatch, str(OWNER))
    assert admin.is_owner(INTRUDER) is False


def test_is_owner_false_for_none(monkeypatch):
    admin = _reload_admin(monkeypatch, str(OWNER))
    assert admin.is_owner(None) is False


def test_is_owner_false_when_env_unset(monkeypatch):
    admin = _reload_admin(monkeypatch, "0")
    # Nobody is the owner when env is unset — guards against accidental wide-open admin.
    assert admin.is_owner(OWNER) is False
    assert admin.is_owner(INTRUDER) is False


def test_is_owner_false_when_env_garbage(monkeypatch):
    admin = _reload_admin(monkeypatch, "not-a-number")
    assert admin.is_owner(OWNER) is False
