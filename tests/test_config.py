import os
import stat
from pathlib import Path

import pytest

from lib.config import CONFIG_KEYS, ConfigError, PscPlotConfig

# --- create_minimal ---


def test_create_minimal():
    config = PscPlotConfig.create_minimal()
    assert config.data_root == Path.cwd()
    assert config.ffmpeg_bin is None
    assert (config.dask_scheduler, config.dask_num_workers, config.dask_chunk_size) == ("synchronous", 1, 1_000_000)
    assert (config.registries_use_defaults, config.registry_patterns) == (True, [])


def test_create_minimal_overrides():
    config = PscPlotConfig.create_minimal(data_root=Path("/data"), dask_num_workers=4)
    assert (config.data_root, config.dask_num_workers, config.dask_scheduler) == (Path("/data"), 4, "synchronous")


def test_fields_have_no_defaults():
    with pytest.raises(TypeError):
        PscPlotConfig(data_root=Path("."))


# --- from_mapping ---


def _complete(**overrides) -> dict:
    values = {
        "PSC_PLOT_DATA_DIR": "data",
        "PSC_PLOT_FFMPEG_BIN": None,
        "PSC_PLOT_DASK_SCHEDULER": "processes",
        "PSC_PLOT_DASK_NUM_WORKERS": "3",
        "PSC_PLOT_DASK_CHUNK_SIZE": "500",
        "PSC_PLOT_REGISTRIES_USE_DEFAULTS": "false",
        "PSC_PLOT_REGISTRIES": ["a.yml"],
    }
    return values | {f"PSC_PLOT_{key}": value for key, value in overrides.items()}


def test_from_mapping():
    config = PscPlotConfig.from_mapping(_complete())
    assert config.data_root == Path("data")
    assert config.ffmpeg_bin is None
    assert (config.dask_scheduler, config.dask_num_workers, config.dask_chunk_size) == ("processes", 3, 500)
    assert (config.registries_use_defaults, config.registry_patterns) == (False, ["a.yml"])


def test_config_keys_match_mapping():
    assert set(CONFIG_KEYS) == set(_complete())


def test_missing_key():
    values = _complete()
    del values["PSC_PLOT_DASK_CHUNK_SIZE"]
    with pytest.raises(ConfigError, match="missing.*PSC_PLOT_DASK_CHUNK_SIZE"):
        PscPlotConfig.from_mapping(values)


@pytest.mark.parametrize(
    "key, value",
    [
        ("DASK_NUM_WORKERS", "four"),
        ("DASK_NUM_WORKERS", "0"),
        ("DASK_NUM_WORKERS", ""),
        ("DASK_NUM_WORKERS", "4.0"),
        ("DASK_CHUNK_SIZE", "-5"),
        ("DASK_SCHEDULER", "fast"),
        ("REGISTRIES_USE_DEFAULTS", "maybe"),
    ],
)
def test_bad_values(key, value):
    with pytest.raises(ConfigError, match=f"PSC_PLOT_{key}"):
        PscPlotConfig.from_mapping(_complete(**{key: value}))


@pytest.mark.parametrize(
    "key, value, match",
    [
        ("DASK_NUM_WORKERS", ["1"], "expected a single value"),
        ("DATA_DIR", None, "expected a single value"),
        ("DASK_SCHEDULER", None, "expected a single value"),
        ("REGISTRIES", "a.yml", "expected a list"),
        ("REGISTRIES", ["a.yml", 3], "expected a list"),
    ],
)
def test_wrong_types(key, value, match):
    with pytest.raises(ConfigError, match=f"PSC_PLOT_{key}: {match}"):
        PscPlotConfig.from_mapping(_complete(**{key: value}))


def test_registries_null_means_none():
    assert PscPlotConfig.from_mapping(_complete(REGISTRIES=None)).registry_patterns == []


@pytest.mark.parametrize("scheduler", ["threads", "processes", "synchronous", "distributed"])
def test_schedulers(scheduler):
    assert PscPlotConfig.from_mapping(_complete(DASK_SCHEDULER=scheduler)).dask_scheduler == scheduler


def _fake_executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_ffmpeg_bin(tmp_path, monkeypatch):
    ffmpeg = _fake_executable(tmp_path / "ffmpeg")
    monkeypatch.setenv("PATH", str(tmp_path))

    assert PscPlotConfig.from_mapping(_complete(FFMPEG_BIN="ffmpeg")).ffmpeg_bin == ffmpeg
    assert PscPlotConfig.from_mapping(_complete(FFMPEG_BIN=str(ffmpeg))).ffmpeg_bin == ffmpeg
    assert PscPlotConfig.from_mapping(_complete(FFMPEG_BIN=None)).ffmpeg_bin is None
    assert PscPlotConfig.from_mapping(_complete(FFMPEG_BIN="")).ffmpeg_bin is None

    for missing in ["no-such-ffmpeg", str(tmp_path / "nope" / "ffmpeg")]:
        with pytest.warns(UserWarning, match="PSC_PLOT_FFMPEG_BIN"):
            assert PscPlotConfig.from_mapping(_complete(FFMPEG_BIN=missing)).ffmpeg_bin is None
