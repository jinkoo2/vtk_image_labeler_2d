"""Config defaults used by CI and frozen builds when .env is absent."""

from __future__ import annotations

import importlib


def _load_config(monkeypatch):
    import config

    importlib.reload(config)
    # A developer .env next to config.py is applied on import. Clear it so the
    # fallback paths are what this test observes. CI has no .env file.
    monkeypatch.delenv("log_dir", raising=False)
    monkeypatch.delenv("temp_dir", raising=False)
    return config


def test_config_defaults_when_env_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = _load_config(monkeypatch)
    conf = config.get_config()

    assert conf["log_dir"] == "_logs"
    assert conf["temp_dir"] == "_temp"
    assert (tmp_path / "_logs").is_dir()
    assert (tmp_path / "_temp").is_dir()


def test_config_uses_environment_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = _load_config(monkeypatch)
    monkeypatch.setenv("log_dir", "logs-ci")
    monkeypatch.setenv("temp_dir", "temp-ci")
    conf = config.get_config()

    assert conf["log_dir"] == "logs-ci"
    assert conf["temp_dir"] == "temp-ci"
    assert (tmp_path / "logs-ci").is_dir()
    assert (tmp_path / "temp-ci").is_dir()
