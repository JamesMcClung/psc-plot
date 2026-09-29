import importlib.resources
import os
import shutil
from dataclasses import KW_ONLY, dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Callable, Self

from lib.registry import Registry

_DATA_DIR_KEY = "PSC_PLOT_DATA_DIR"
_FFMPEG_BIN_KEY = "PSC_PLOT_FFMPEG_BIN"
_DASK_NUM_WORKERS_KEY = "PSC_PLOT_DASK_NUM_WORKERS"
_DASK_CHUNK_SIZE_KEY = "PSC_PLOT_DASK_CHUNK_SIZE"
_DASK_SCHEDULER_KEY = "PSC_PLOT_DASK_SCHEDULER"
_REGISTRIES_KEY = "PSC_PLOT_REGISTRIES"


def parse_optional[T](s: str | None, parser: Callable[[str], T]) -> T | None:
    if s is None:
        return None
    return parser(s)


def _default_registries_dir() -> Path:
    return Path(str(importlib.resources.files("lib") / "default_registries"))


@dataclass
class PscPlotConfig:
    _: KW_ONLY
    data_root: Path = field(default_factory=Path.cwd)
    ffmpeg_bin: Path | None = None
    dask_num_workers: int = 1
    dask_chunk_size: int = 1_000_000
    dask_scheduler: str | None = None
    registries_dir: Path = field(default_factory=_default_registries_dir)

    @cached_property
    def registry(self) -> Registry:
        return Registry.load(self.registries_dir)

    @classmethod
    def from_env(cls) -> Self:
        config = cls()

        config.data_root = parse_optional(os.environ.get(_DATA_DIR_KEY), Path) or config.data_root
        config.ffmpeg_bin = parse_optional(os.environ.get(_FFMPEG_BIN_KEY, shutil.which("ffmpeg")), Path) or config.ffmpeg_bin
        config.dask_num_workers = parse_optional(os.environ.get(_DASK_NUM_WORKERS_KEY), int) or os.cpu_count() or config.dask_num_workers
        config.dask_chunk_size = parse_optional(os.environ.get(_DASK_CHUNK_SIZE_KEY), int) or config.dask_chunk_size
        config.dask_scheduler = os.environ.get(_DASK_SCHEDULER_KEY) or config.dask_scheduler
        config.registries_dir = parse_optional(os.environ.get(_REGISTRIES_KEY), Path) or config.registries_dir

        return config
