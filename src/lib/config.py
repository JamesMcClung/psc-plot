import os
import shutil
from dataclasses import KW_ONLY, dataclass, field
from pathlib import Path
from typing import Callable, Self

_DATA_DIR_KEY = "PSC_PLOT_DATA_DIR"
_FFMPEG_BIN_KEY = "PSC_PLOT_FFMPEG_BIN"
_DASK_NUM_WORKERS_KEY = "PSC_PLOT_DASK_NUM_WORKERS"
_DASK_CHUNK_SIZE_KEY = "PSC_PLOT_DASK_CHUNK_SIZE"
_DASK_SCHEDULER_KEY = "PSC_PLOT_DASK_SCHEDULER"


def parse_optional[T](s: str | None, parser: Callable[[str], T]) -> T | None:
    if s is None:
        return None
    return parser(s)


@dataclass
class PscPlotConfig:
    _: KW_ONLY
    data_dir: Path = field(default_factory=Path.cwd)
    ffmpeg_bin: Path | None = None
    dask_num_workers: int = 1
    dask_chunk_size: int = 1_000_000
    dask_scheduler: str | None = None

    @classmethod
    def from_env(cls) -> Self:
        config = cls()

        config.data_dir = parse_optional(os.environ.get(_DATA_DIR_KEY), Path) or config.data_dir
        config.ffmpeg_bin = parse_optional(os.environ.get(_FFMPEG_BIN_KEY, shutil.which("ffmpeg")), Path) or config.ffmpeg_bin
        config.dask_num_workers = parse_optional(os.environ.get(_DASK_NUM_WORKERS_KEY), int) or os.cpu_count() or config.dask_num_workers
        config.dask_chunk_size = parse_optional(os.environ.get(_DASK_CHUNK_SIZE_KEY), int) or config.dask_chunk_size
        config.dask_scheduler = os.environ.get(_DASK_SCHEDULER_KEY) or config.dask_scheduler

        return config
