import os
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Self

_DATA_DIR_KEY = "PSC_PLOT_DATA_DIR"
_FFMPEG_BIN_KEY = "PSC_PLOT_FFMPEG_BIN"
_DASK_NUM_WORKERS_KEY = "PSC_PLOT_DASK_NUM_WORKERS"


def parse_optional[T](s: str | None, parser: Callable[[str], T]) -> T | None:
    if s is None:
        return None
    return parser(s)


@dataclass
class PscPlotConfig:
    data_dir: Path
    ffmpeg_bin: Path | None
    dask_num_workers: int

    @classmethod
    def _load(cls) -> Self:
        data_dir = parse_optional(os.environ.get(_DATA_DIR_KEY), Path)
        if not data_dir:
            message = f"Path to data not specified. Set the {_DATA_DIR_KEY} environment variable to specify."
            raise RuntimeError(message)

        ffmpeg_bin = parse_optional(os.environ.get(_FFMPEG_BIN_KEY, shutil.which("ffmpeg")), Path)
        if not ffmpeg_bin:
            message = f"Ffmpeg not found. Ffmpeg is needed to save animated figures. Install ffmpeg and add it to PATH or set {_FFMPEG_BIN_KEY}."
            warnings.warn(message)

        dask_num_workers = parse_optional(os.environ.get(_DASK_NUM_WORKERS_KEY), int)
        if not dask_num_workers:
            dask_num_workers = 1
            message = f"Number of dask workers not specified; defaulting to {dask_num_workers}. Set {_DASK_NUM_WORKERS_KEY} to specify."
            warnings.warn(message)

        return cls(data_dir, ffmpeg_bin, dask_num_workers)


CONFIG = PscPlotConfig._load()
