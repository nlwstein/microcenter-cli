from __future__ import annotations

import pytest

from microcenter_cli import config as config_module
from microcenter_cli.config import Config, ConfigError, _clamp, load_config


def test_clamp_fixes_below_minimum_values(capsys):
    cfg = Config(request_timeout_seconds=0, max_retries=0, min_request_interval_seconds=-1)
    _clamp(cfg)
    assert cfg.request_timeout_seconds == 1.0
    assert cfg.max_retries == 1
    assert cfg.min_request_interval_seconds == 0.0
    assert "warning" in capsys.readouterr().err


def test_clamp_leaves_sane_values_alone():
    cfg = Config(request_timeout_seconds=45.0, max_retries=5)
    _clamp(cfg)
    assert cfg.request_timeout_seconds == 45.0
    assert cfg.max_retries == 5


def test_load_config_defaults_when_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "does-not-exist.toml")
    cfg = load_config()
    assert cfg.default_store is None
    assert cfg.max_retries == 3


def test_load_config_raises_clear_error_on_malformed_toml(monkeypatch, tmp_path):
    bad_file = tmp_path / "config.toml"
    bad_file.write_text("this is not [ valid toml")
    monkeypatch.setattr(config_module, "CONFIG_FILE", bad_file)
    with pytest.raises(ConfigError, match="couldn't parse"):
        load_config()


def test_load_config_applies_clamping_from_file(monkeypatch, tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("request_timeout_seconds = 0\n")
    monkeypatch.setattr(config_module, "CONFIG_FILE", cfg_file)
    cfg = load_config()
    assert cfg.request_timeout_seconds == 1.0
