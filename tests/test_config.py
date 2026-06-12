"""Tests for environment-driven configuration."""

from pathlib import Path

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


@pytest.mark.parametrize(
    "bogus",
    ["totally-not-a-model", "gpt-4o", "gemmini-2.5-flash", "gemini-", "Gemini-2.5"],
)
def test_model_name_rejects_invalid(monkeypatch, bogus):
    monkeypatch.setenv("GOOGLE_MODEL", bogus)
    with pytest.raises(SystemExit):
        config.model_name()


def test_db_url_default_is_absolute_and_cwd_independent(monkeypatch):
    monkeypatch.delenv("ADK_DB_PATH", raising=False)
    url = config.db_url()
    assert url.startswith("sqlite:///")
    path = url.removeprefix("sqlite:///")
    assert Path(path).is_absolute()
    assert path != config.DEFAULT_DB_FILENAME


def test_db_url_override(monkeypatch, tmp_path):
    target = tmp_path / "sessions.db"
    monkeypatch.setenv("ADK_DB_PATH", str(target))
    assert config.db_url().endswith("sessions.db")


def test_order_threshold_default(monkeypatch):
    monkeypatch.delenv("LARGE_ORDER_THRESHOLD", raising=False)
    assert config.order_threshold() == config.DEFAULT_LARGE_ORDER_THRESHOLD


def test_order_threshold_override(monkeypatch):
    monkeypatch.setenv("LARGE_ORDER_THRESHOLD", "2")
    assert config.order_threshold() == 2


def test_order_threshold_blank_falls_back(monkeypatch):
    monkeypatch.setenv("LARGE_ORDER_THRESHOLD", "   ")
    assert config.order_threshold() == config.DEFAULT_LARGE_ORDER_THRESHOLD


@pytest.mark.parametrize("bad", ["abc", "1.5", "-3"])
def test_order_threshold_invalid(monkeypatch, bad):
    monkeypatch.setenv("LARGE_ORDER_THRESHOLD", bad)
    with pytest.raises(SystemExit):
        config.order_threshold()


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
