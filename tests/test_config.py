"""Tests for environment-driven configuration."""

import pytest

from ai_agents import config


def test_model_name_default(monkeypatch):
    monkeypatch.delenv("GOOGLE_MODEL", raising=False)
    assert config.model_name() == config.DEFAULT_MODEL


def test_model_name_override(monkeypatch):
    monkeypatch.setenv("GOOGLE_MODEL", "gemini-2.5-pro")
    assert config.model_name() == "gemini-2.5-pro"


def test_model_name_blank_falls_back(monkeypatch):
    monkeypatch.setenv("GOOGLE_MODEL", "   ")
    assert config.model_name() == config.DEFAULT_MODEL


def test_db_url_default(monkeypatch):
    monkeypatch.delenv("ADK_DB_PATH", raising=False)
    assert config.db_url() == f"sqlite:///{config.DEFAULT_DB_PATH}"


def test_db_url_override(monkeypatch):
    monkeypatch.setenv("ADK_DB_PATH", "/tmp/x.db")
    assert config.db_url() == "sqlite:////tmp/x.db"


def test_require_api_key_returns_value(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "abc123")
    assert config.require_api_key() == "abc123"


def test_require_api_key_missing(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        config.require_api_key()


def test_require_api_key_blank(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "   ")
    with pytest.raises(SystemExit):
        config.require_api_key()
