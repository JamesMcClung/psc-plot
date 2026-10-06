import os
import stat
from pathlib import Path

import pytest

from lib.config import CONFIG_KEYS, CONFIG_PATH_KEY, ConfigError, PscPlotConfig

# --- create_minimal ---


def test_create_minimal():
    config = PscPlotConfig.create_minimal()
    assert config.data_root == Path.cwd()
    assert config.ffmpeg_bin is None
    assert (config.dask_scheduler, config.dask_num_workers, config.dask_chunk_size) == ("synchronous", 1, 1_000_000)
    assert (config.registries_use_defaults, config.registry_patterns) == (True, [])


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
        with pytest.warns(UserWarning, match="PSC_PLOT_FFMPEG_BIN.*set it to null"):
            assert PscPlotConfig.from_mapping(_complete(FFMPEG_BIN=missing)).ffmpeg_bin is None


# --- from_env ---

_FULL = """\
PSC_PLOT_DATA_DIR: data
PSC_PLOT_FFMPEG_BIN: null
PSC_PLOT_DASK_SCHEDULER: processes
PSC_PLOT_DASK_NUM_WORKERS: 3
PSC_PLOT_DASK_CHUNK_SIZE: 500
PSC_PLOT_REGISTRIES_USE_DEFAULTS: false
PSC_PLOT_REGISTRIES: [a.yml]
"""


@pytest.fixture
def clean_env(monkeypatch):
    for key in (*CONFIG_KEYS, CONFIG_PATH_KEY):
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def _use_config(monkeypatch, tmp_path, text: str, replace: dict[str, str] | None = None) -> Path:
    for old, new in (replace or {}).items():
        assert old in text
        text = text.replace(old, new)
    path = tmp_path / "config.yml"
    path.write_text(text)
    monkeypatch.setenv(CONFIG_PATH_KEY, str(path))
    return path


def test_shipped_config(clean_env):
    config = PscPlotConfig.from_env()
    assert config.data_root == Path(".")
    assert (config.dask_scheduler, config.dask_num_workers, config.dask_chunk_size) == ("threads", 1, 1_000_000)
    assert (config.registries_use_defaults, config.registry_patterns) == (True, [])


def test_user_config(clean_env, tmp_path):
    _use_config(clean_env, tmp_path, _FULL)
    config = PscPlotConfig.from_env()
    assert config == PscPlotConfig.from_mapping(_complete())


def test_user_config_replaces_shipped(clean_env, tmp_path):
    _use_config(clean_env, tmp_path, _FULL, {"PSC_PLOT_DASK_CHUNK_SIZE: 500\n": ""})
    with pytest.raises(ConfigError, match="missing.*PSC_PLOT_DASK_CHUNK_SIZE"):
        PscPlotConfig.from_env()


def test_relative_config_path(clean_env, tmp_path):
    clean_env.chdir(tmp_path)
    (tmp_path / "c.yml").write_text(_FULL)
    clean_env.setenv(CONFIG_PATH_KEY, "c.yml")
    assert PscPlotConfig.from_env().dask_num_workers == 3


def test_env_overrides_file(clean_env, tmp_path):
    _use_config(clean_env, tmp_path, _FULL)
    clean_env.setenv("PSC_PLOT_DASK_NUM_WORKERS", "7")
    clean_env.setenv("PSC_PLOT_REGISTRIES", f"x.yml{os.pathsep}y/*.yml")
    clean_env.setenv("PSC_PLOT_FFMPEG_BIN", "")
    config = PscPlotConfig.from_env()
    assert (config.dask_num_workers, config.registry_patterns, config.ffmpeg_bin) == (7, ["x.yml", "y/*.yml"], None)


def test_env_completes_file(clean_env, tmp_path):
    _use_config(clean_env, tmp_path, _FULL, {"PSC_PLOT_DASK_CHUNK_SIZE: 500\n": ""})
    clean_env.setenv("PSC_PLOT_DASK_CHUNK_SIZE", "9")
    assert PscPlotConfig.from_env().dask_chunk_size == 9


@pytest.mark.parametrize(
    "line, env, field, expected",
    [
        ("PSC_PLOT_DASK_NUM_WORKERS: $NSLOTS", {"NSLOTS": "5"}, "dask_num_workers", 5),
        ("PSC_PLOT_DASK_NUM_WORKERS: ${NSLOTS}", {"NSLOTS": "5"}, "dask_num_workers", 5),
        ("PSC_PLOT_DATA_DIR: ${ROOT}/x", {"ROOT": "r"}, "data_root", Path("r/x")),
        ("PSC_PLOT_DATA_DIR: a$$b", {}, "data_root", Path("a$b")),
        ("PSC_PLOT_DATA_DIR: a$", {}, "data_root", Path("a$")),
        ("PSC_PLOT_DATA_DIR: a$-b", {}, "data_root", Path("a$-b")),
        ("PSC_PLOT_REGISTRIES: [$R/a.yml, b.yml]", {"R": "r"}, "registry_patterns", ["r/a.yml", "b.yml"]),
    ],
)
def test_expansion(clean_env, tmp_path, line, env, field, expected):
    key = line.split(":")[0]
    old_line = next(old for old in _FULL.splitlines() if old.startswith(key + ":"))
    _use_config(clean_env, tmp_path, _FULL, {old_line: line})
    for name, value in env.items():
        clean_env.setenv(name, value)
    assert getattr(PscPlotConfig.from_env(), field) == expected


def test_unset_variable_errors(clean_env, tmp_path):
    clean_env.delenv("NSLOTS", raising=False)
    _use_config(clean_env, tmp_path, _FULL, {"PSC_PLOT_DASK_NUM_WORKERS: 3": "PSC_PLOT_DASK_NUM_WORKERS: $NSLOTS"})
    with pytest.raises(ConfigError, match=r"PSC_PLOT_DASK_NUM_WORKERS: .*\$NSLOTS"):
        PscPlotConfig.from_env()


def test_env_overridden_key_is_not_expanded(clean_env, tmp_path):
    clean_env.delenv("NSLOTS", raising=False)
    _use_config(clean_env, tmp_path, _FULL, {"PSC_PLOT_DASK_NUM_WORKERS: 3": "PSC_PLOT_DASK_NUM_WORKERS: $NSLOTS"})
    clean_env.setenv("PSC_PLOT_DASK_NUM_WORKERS", "2")
    assert PscPlotConfig.from_env().dask_num_workers == 2


def test_env_values_are_not_expanded(clean_env, tmp_path):
    _use_config(clean_env, tmp_path, _FULL)
    clean_env.setenv("PSC_PLOT_DATA_DIR", "$NOT_EXPANDED")
    assert PscPlotConfig.from_env().data_root == Path("$NOT_EXPANDED")


def test_yaml_native_scalars(clean_env, tmp_path):
    _use_config(clean_env, tmp_path, _FULL, {"PSC_PLOT_DASK_CHUNK_SIZE: 500": "PSC_PLOT_DASK_CHUNK_SIZE: 1_000_000", "PSC_PLOT_REGISTRIES_USE_DEFAULTS: false": "PSC_PLOT_REGISTRIES_USE_DEFAULTS: True", "PSC_PLOT_FFMPEG_BIN: null": "PSC_PLOT_FFMPEG_BIN: ~"})
    config = PscPlotConfig.from_env()
    assert (config.dask_chunk_size, config.registries_use_defaults, config.ffmpeg_bin) == (1_000_000, True, None)


@pytest.mark.parametrize(
    "line, field, expected",
    [
        ("PSC_PLOT_DATA_DIR: 0755", "data_root", Path("0755")),
        ("PSC_PLOT_DATA_DIR: 2026-10-06", "data_root", Path("2026-10-06")),
        ("PSC_PLOT_DATA_DIR: no", "data_root", Path("no")),
        ("PSC_PLOT_REGISTRIES: [1.10]", "registry_patterns", ["1.10"]),
        ("PSC_PLOT_DASK_NUM_WORKERS: 010", "dask_num_workers", 10),
    ],
)
def test_file_values_are_literal_text(clean_env, tmp_path, line, field, expected):
    key = line.split(":")[0]
    old_line = next(old for old in _FULL.splitlines() if old.startswith(key + ":"))
    _use_config(clean_env, tmp_path, _FULL, {old_line: line})
    assert getattr(PscPlotConfig.from_env(), field) == expected


@pytest.mark.parametrize(
    "text, match",
    [
        ("- a\n- b\n", "expected a mapping"),
        (_FULL + "PSC_PLOT_DASK_WORKERS: 4\n", r"unknown key.*PSC_PLOT_DASK_WORKERS"),
        (_FULL + "PSC_PLOT_CONFIG_PATH: x.yml\n", r"unknown key.*PSC_PLOT_CONFIG_PATH"),
        ("", "missing"),
        (_FULL.replace("PSC_PLOT_DATA_DIR: data", "PSC_PLOT_DATA_DIR: {a: b}"), "PSC_PLOT_DATA_DIR: expected a scalar"),
        (_FULL.replace("PSC_PLOT_REGISTRIES: [a.yml]", "PSC_PLOT_REGISTRIES: a.yml"), "PSC_PLOT_REGISTRIES: expected a list"),
        ("PSC_PLOT_DATA_DIR: [unclosed\n", "config.yml"),
    ],
)
def test_file_errors(clean_env, tmp_path, text, match):
    _use_config(clean_env, tmp_path, text)
    with pytest.raises(ConfigError, match=match):
        PscPlotConfig.from_env()


def test_missing_config_file(clean_env, tmp_path):
    clean_env.setenv(CONFIG_PATH_KEY, str(tmp_path / "nope.yml"))
    with pytest.raises(ConfigError, match="nope.yml does not exist"):
        PscPlotConfig.from_env()
