import json

import pytest

from debate_sdk.shared.config import load_logging_config, load_rate_limits, load_setup_config
from debate_sdk.shared.config_utils import normalize_logging_config, normalize_setup_config


def test_load_setup_config_rejects_non_object_root(tmp_path):
    cfg_path = tmp_path / "setup.json"
    cfg_path.write_text(json.dumps(["bad"]), encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a JSON object"):
        load_setup_config(cfg_path)


def test_load_logging_config_supports_default_project_root(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "logging_config.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.00",
                "log_directory": "results/logs",
                "max_files": 3,
                "max_lines_per_file": 20,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("debate_sdk.shared.config._project_root", lambda: tmp_path)

    config = load_logging_config()

    assert config["max_files"] == 3
    assert config["log_level"] == "INFO"


def test_load_logging_config_rejects_invalid_root_and_normalize_setup_extra_branches(tmp_path):
    cfg_path = tmp_path / "logging.json"
    cfg_path.write_text(json.dumps(["bad"]), encoding="utf-8")

    with pytest.raises(ValueError, match="Logging config root must be a JSON object"):
        load_logging_config(cfg_path)

    with pytest.raises(ValueError, match="Field 'debate' must be a JSON object"):
        normalize_setup_config(
            {
                "version": "1.00",
                "watchdog": {"timeout_seconds": 1, "check_interval_seconds": 1},
                "debate": "bad",
            }
        )


def test_config_loaders_raise_for_missing_or_non_object_files(tmp_path):
    with pytest.raises(ValueError, match="Setup config error"):
        load_setup_config(tmp_path / "missing-setup.json")

    with pytest.raises(ValueError, match="Logging config error"):
        load_logging_config(tmp_path / "missing-logging.json")

    rate_path = tmp_path / "rate_limits.json"
    rate_path.write_text(json.dumps(["bad"]), encoding="utf-8")
    with pytest.raises(ValueError, match="Rate limit config root must be a JSON object"):
        load_rate_limits(rate_path)


def test_normalize_helpers_cover_missing_fields_and_invalid_values():
    with pytest.raises(ValueError, match="Missing required debate field: con_persona"):
        normalize_setup_config(
            {
                "version": "1.00",
                "watchdog": {"timeout_seconds": 1, "check_interval_seconds": 1},
                "debate": {"rounds": 2, "model": "x", "pro_persona": "p"},
            }
        )

    with pytest.raises(ValueError, match="debate.rounds"):
        normalize_setup_config(
            {
                "version": "1.00",
                "watchdog": {"timeout_seconds": 1, "check_interval_seconds": 1},
                "debate": {
                    "rounds": 0,
                    "model": "x",
                    "pro_persona": "p",
                    "con_persona": "c",
                },
            }
        )

    with pytest.raises(ValueError, match="Missing required logging fields"):
        normalize_logging_config({"version": "1.00", "log_directory": "logs"})

    with pytest.raises(ValueError, match="max_lines_per_file"):
        normalize_logging_config(
            {
                "version": "1.00",
                "log_directory": "logs",
                "max_files": 2,
                "max_lines_per_file": 0,
            }
        )