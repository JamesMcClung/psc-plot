import glob
import importlib.resources
import os
import shutil
import warnings
from collections.abc import Mapping
from dataclasses import KW_ONLY, dataclass, replace
from functools import cached_property
from pathlib import Path
from typing import Callable, Self

from lib.registry import Registry, RegistryError

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


def parse_optional[T](s: str | None, parser: Callable[[str], T]) -> T | None:
    if s is None:
        return None
    return parser(s)


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
        warnings.warn(f"{_FFMPEG_BIN_KEY}: {s!r} not found; saving animations is unavailable")
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
        environ = os.environ
        return cls(
            data_root=parse_optional(environ.get(_DATA_DIR_KEY), Path) or Path.cwd(),
            ffmpeg_bin=parse_optional(environ.get(_FFMPEG_BIN_KEY, shutil.which("ffmpeg")), Path),
            dask_num_workers=parse_optional(environ.get(_DASK_NUM_WORKERS_KEY), int) or os.cpu_count() or 1,
            dask_chunk_size=parse_optional(environ.get(_DASK_CHUNK_SIZE_KEY), int) or 1_000_000,
            dask_scheduler=environ.get(_DASK_SCHEDULER_KEY) or "threads",
            registries_use_defaults=_parse_bool(environ.get(_REGISTRIES_USE_DEFAULTS_KEY, "true")),
            registry_patterns=_split_patterns(environ.get(_REGISTRIES_KEY, "")),
        )
