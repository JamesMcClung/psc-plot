import glob
import importlib.resources
import math
import os
import re
import shutil
import warnings
from collections.abc import Collection, Mapping
from dataclasses import KW_ONLY, dataclass, replace
from functools import cached_property
from pathlib import Path
from typing import Callable, Self

import yaml

from lib.registry import Registry, RegistryError

CONFIG_PATH_KEY = "PSC_PLOT_CONFIG_PATH"
_DATA_DIR_KEY = "PSC_PLOT_DATA_DIR"
_FFMPEG_BIN_KEY = "PSC_PLOT_FFMPEG_BIN"
_DASK_NUM_WORKERS_KEY = "PSC_PLOT_DASK_NUM_WORKERS"
_DASK_CHUNK_SIZE_KEY = "PSC_PLOT_DASK_CHUNK_SIZE"
_DASK_SCHEDULER_KEY = "PSC_PLOT_DASK_SCHEDULER"
_REGISTRIES_USE_DEFAULTS_KEY = "PSC_PLOT_REGISTRIES_USE_DEFAULTS"
_REGISTRIES_KEY = "PSC_PLOT_REGISTRIES"
_GLOB_CHARS = "*?["
SCHEDULERS = ("threads", "processes", "synchronous", "distributed")


class ConfigError(ValueError): ...


type ConfigValue = str | list[str] | None


def _default_registries_dir() -> Path:
    return Path(str(importlib.resources.files("lib") / "default_registries"))


def _parse_bool(s: str) -> bool:
    match s.lower():
        case "true" | "1":
            return True
        case "false" | "0":
            return False
    raise ValueError(f"expected true/false/1/0, got {s!r}")


def _parse_positive_int(s: str) -> int:
    value = int(s)
    if value < 1:
        raise ValueError(f"must be positive, got {value}")
    return value


def _parse_scheduler(s: str) -> str:
    if s not in SCHEDULERS:
        raise ValueError(f"expected one of {list(SCHEDULERS)}, got {s!r}")
    return s


def _parse_ffmpeg_bin(s: str) -> Path | None:
    if not s:
        return None
    if (found := shutil.which(s)) is None:
        warnings.warn(f"{_FFMPEG_BIN_KEY}: {s!r} not found; saving animations is unavailable. If that's intended, set it to null in the config file.")
        return None
    return Path(found)


_SCALAR_PARSERS: dict[str, Callable[[str], object]] = {
    _DATA_DIR_KEY: Path,
    _FFMPEG_BIN_KEY: _parse_ffmpeg_bin,
    _DASK_SCHEDULER_KEY: _parse_scheduler,
    _DASK_NUM_WORKERS_KEY: _parse_positive_int,
    _DASK_CHUNK_SIZE_KEY: _parse_positive_int,
    _REGISTRIES_USE_DEFAULTS_KEY: _parse_bool,
}
_NULLABLE_SCALAR_KEYS = {_FFMPEG_BIN_KEY}
CONFIG_KEYS = (*_SCALAR_PARSERS, _REGISTRIES_KEY)


def _default_config_path() -> Path:
    return Path(str(importlib.resources.files("lib") / "default_config.yml"))


def config_file_path_from_env(environ: Mapping[str, str]) -> Path:
    """The config file to read: $PSC_PLOT_CONFIG_PATH, or the shipped default_config.yml."""
    return Path(environ[CONFIG_PATH_KEY]) if CONFIG_PATH_KEY in environ else _default_config_path()


# $$ (escape), ${NAME}, or $NAME; a $ followed by anything else is left alone
_VAR_PATTERN = re.compile(r"\$(?:(\$)|\{(\w+)\}|(\w+))")


class _LiteralLoader(yaml.SafeLoader):
    """A SafeLoader that reads every scalar but null as its literal text, so `0755`, `2026-10-06`, and `no` stay strings and parse like env values."""


_LiteralLoader.yaml_implicit_resolvers = {first: [(tag, regexp) for tag, regexp in resolvers if tag == "tag:yaml.org,2002:null"] for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()}


def format_config_value(value: ConfigValue) -> str:
    """YAML text that a config file reads back as `value`: plain where the literal loader allows, else quoted."""
    if isinstance(value, str):
        try:
            if yaml.load(f"k: {value}", _LiteralLoader) == {"k": value}:
                return value
        except yaml.YAMLError:
            pass
    return yaml.safe_dump(value, default_flow_style=True, width=math.inf).removesuffix("\n...\n").removesuffix("\n")


def _expand_vars(value: str, environ: Mapping[str, str]) -> str:
    def substitute(match: re.Match) -> str:
        if match[1]:
            return "$"
        name = match[2] or match[3]
        if name not in environ:
            raise ConfigError(f"references unset variable ${name}")
        return environ[name]

    return _VAR_PATTERN.sub(substitute, value)


def _require_scalar(raw: object) -> str:
    if not isinstance(raw, str):
        raise ConfigError(f"expected a scalar, got {raw!r}")
    return raw


def _to_config_value(raw: object, environ: Mapping[str, str]) -> ConfigValue:
    if raw is None:
        return None
    if isinstance(raw, list):
        return [_expand_vars(_require_scalar(item), environ) for item in raw]
    return _expand_vars(_require_scalar(raw), environ)


def _read_config_file(path: Path, environ: Mapping[str, str], overridden_keys: Collection[str]) -> dict[str, ConfigValue]:
    if not path.is_file():
        raise ConfigError(f"config file {path} does not exist")
    try:
        with path.open() as f:
            content = yaml.load(f, Loader=_LiteralLoader)
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: {e}") from e

    if content is None:
        content = {}
    if not isinstance(content, dict):
        raise ConfigError(f"{path}: expected a mapping of PSC_PLOT_* keys to values")
    if unknown := sorted(str(key) for key in content if key not in CONFIG_KEYS):
        raise ConfigError(f"{path}: unknown key(s) {unknown}; expected some of {list(CONFIG_KEYS)}")

    values = {}
    for key, raw in content.items():
        if key in overridden_keys:
            continue
        try:
            values[key] = _to_config_value(raw, environ)
        except ConfigError as e:
            raise ConfigError(f"{path}: {key}: {e}") from e
    return values


def _split_patterns(s: str) -> list[str]:
    return [pattern for pattern in s.split(os.pathsep) if pattern]


def _expand_registry_pattern(pattern: str) -> list[Path]:
    if any(char in pattern for char in _GLOB_CHARS):
        paths = sorted(Path(match) for match in glob.glob(pattern))
        if not paths:
            raise RegistryError(f"registry pattern {pattern!r} matches no files")
    else:
        paths = [Path(pattern)]
        if not paths[0].exists():
            raise RegistryError(f"registry file {pattern} does not exist")

    for path in paths:
        if path.is_dir():
            raise RegistryError(f"{path} is a directory; list its files, e.g. {path}/*.yml")
    return paths


@dataclass
class PscPlotConfig:
    _: KW_ONLY
    data_root: Path
    ffmpeg_bin: Path | None
    dask_num_workers: int
    dask_chunk_size: int
    dask_scheduler: str
    registries_use_defaults: bool
    registry_patterns: list[str]

    @classmethod
    def create_minimal(cls, **overrides) -> Self:
        """The minimal viable config: no parallelism and no ffmpeg. For tests and convenience; never used as a fallback."""
        minimal = cls(
            data_root=Path.cwd(),
            ffmpeg_bin=None,
            dask_num_workers=1,
            dask_chunk_size=1_000_000,
            dask_scheduler="synchronous",
            registries_use_defaults=True,
            registry_patterns=[],
        )
        return replace(minimal, **overrides)

    @classmethod
    def from_mapping(cls, values: Mapping[str, ConfigValue]) -> Self:
        """Parse a complete config from `PSC_PLOT_*` keys. `PSC_PLOT_REGISTRIES` is a list (or None); every other key is a string."""
        if missing := [key for key in CONFIG_KEYS if key not in values]:
            raise ConfigError(f"missing config key(s) {missing}; set them in the config file or the env")

        def scalar(key: str):
            value = values[key]
            if value is None and key in _NULLABLE_SCALAR_KEYS:
                return None
            if not isinstance(value, str):
                raise ConfigError(f"{key}: expected a single value, got {value!r}")
            try:
                return _SCALAR_PARSERS[key](value)
            except ValueError as e:
                raise ConfigError(f"{key}: {e}") from e

        patterns = values[_REGISTRIES_KEY]
        if patterns is None:
            patterns = []
        if not isinstance(patterns, list) or not all(isinstance(pattern, str) for pattern in patterns):
            raise ConfigError(f"{_REGISTRIES_KEY}: expected a list of paths, got {patterns!r}")

        return cls(
            data_root=scalar(_DATA_DIR_KEY),
            ffmpeg_bin=scalar(_FFMPEG_BIN_KEY),
            dask_scheduler=scalar(_DASK_SCHEDULER_KEY),
            dask_num_workers=scalar(_DASK_NUM_WORKERS_KEY),
            dask_chunk_size=scalar(_DASK_CHUNK_SIZE_KEY),
            registries_use_defaults=scalar(_REGISTRIES_USE_DEFAULTS_KEY),
            registry_patterns=patterns,
        )

    def to_mapping(self) -> dict[str, ConfigValue]:
        """The `PSC_PLOT_*` keys and values that `from_mapping` parses back into this config."""
        return {
            _DATA_DIR_KEY: str(self.data_root),
            _FFMPEG_BIN_KEY: None if self.ffmpeg_bin is None else str(self.ffmpeg_bin),
            _DASK_SCHEDULER_KEY: self.dask_scheduler,
            _DASK_NUM_WORKERS_KEY: str(self.dask_num_workers),
            _DASK_CHUNK_SIZE_KEY: str(self.dask_chunk_size),
            _REGISTRIES_USE_DEFAULTS_KEY: "true" if self.registries_use_defaults else "false",
            _REGISTRIES_KEY: list(self.registry_patterns),
        }

    @property
    def registry_files(self) -> list[Path]:
        files = sorted(_default_registries_dir().glob("*.yml")) if self.registries_use_defaults else []
        for pattern in self.registry_patterns:
            files.extend(_expand_registry_pattern(pattern))
        return files

    @cached_property
    def registry(self) -> Registry:
        return Registry.load(self.registry_files)

    @classmethod
    def from_env(cls) -> Self:
        """Read the config file ($PSC_PLOT_CONFIG_PATH, or the shipped default_config.yml) and overlay the env's PSC_PLOT_* vars."""
        environ = os.environ
        config_path = config_file_path_from_env(environ)

        env_values: dict[str, ConfigValue] = {key: environ[key] for key in CONFIG_KEYS if key in environ}
        if _REGISTRIES_KEY in env_values:
            env_values[_REGISTRIES_KEY] = _split_patterns(env_values[_REGISTRIES_KEY])

        file_values = _read_config_file(config_path, environ, overridden_keys=env_values.keys())
        return cls.from_mapping(file_values | env_values)
