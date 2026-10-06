import glob
import importlib.resources
import os
import shutil
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
