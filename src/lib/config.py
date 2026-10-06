import glob
import importlib.resources
import os
import shutil
from dataclasses import KW_ONLY, dataclass, field
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
    data_root: Path = field(default_factory=Path.cwd)
    ffmpeg_bin: Path | None = None
    dask_num_workers: int = 1
    dask_chunk_size: int = 1_000_000
    dask_scheduler: str | None = None
    registries_use_defaults: bool = True
    registry_patterns: list[str] = field(default_factory=list)

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
        config = cls()

        config.data_root = parse_optional(os.environ.get(_DATA_DIR_KEY), Path) or config.data_root
        config.ffmpeg_bin = parse_optional(os.environ.get(_FFMPEG_BIN_KEY, shutil.which("ffmpeg")), Path) or config.ffmpeg_bin
        config.dask_num_workers = parse_optional(os.environ.get(_DASK_NUM_WORKERS_KEY), int) or os.cpu_count() or config.dask_num_workers
        config.dask_chunk_size = parse_optional(os.environ.get(_DASK_CHUNK_SIZE_KEY), int) or config.dask_chunk_size
        config.dask_scheduler = os.environ.get(_DASK_SCHEDULER_KEY) or config.dask_scheduler
        if (use_defaults := os.environ.get(_REGISTRIES_USE_DEFAULTS_KEY)) is not None:
            config.registries_use_defaults = _parse_bool(use_defaults)
        config.registry_patterns = parse_optional(os.environ.get(_REGISTRIES_KEY), _split_patterns) or config.registry_patterns

        return config
