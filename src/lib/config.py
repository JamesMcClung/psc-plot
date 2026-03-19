import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

_DATA_DIR_KEY = "PSC_PLOT_DATA_DIR"
_FFMPEG_BIN_KEY = "PSC_PLOT_FFMPEG_BIN"


def maybe_str_to_maybe_path(s: str | None) -> Path | None:
    if s is None:
        return None
    return Path(s)


@dataclass
class PscPlotConfig:
    data_dir: Path
    ffmpeg_bin: Path | None

    @classmethod
    def _load(cls) -> Self:
        data_dir = maybe_str_to_maybe_path(os.environ.get(_DATA_DIR_KEY))
        if not data_dir:
            message = f"Path to data not specified. Set the {_DATA_DIR_KEY} environment variable to specify."
            raise RuntimeError(message)

        ffmpeg_bin = maybe_str_to_maybe_path(os.environ.get(_FFMPEG_BIN_KEY))

        return cls(data_dir, ffmpeg_bin)


CONFIG = PscPlotConfig._load()
