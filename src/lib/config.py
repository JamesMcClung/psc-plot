import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

_ROOT_DATA_PATH_ENV_VAR_NAME = "PSC_PLOT_ROOT_DATA_PATH"
_FFMPEG_BIN_ENV_VAR_NAME = "PSC_PLOT_FFMPEG_BIN"


@dataclass
class PscPlotConfig:
    data_dir: Path
    ffmpeg_bin: Path | None

    @classmethod
    def _load(cls) -> Self:
        data_dir = os.environ.get(_ROOT_DATA_PATH_ENV_VAR_NAME)
        if not data_dir:
            message = f"Path to data not specified. Set the {_ROOT_DATA_PATH_ENV_VAR_NAME} environment variable to specify."
            raise RuntimeError(message)

        ffmpeg_bin = os.environ.get(_FFMPEG_BIN_ENV_VAR_NAME)

        return cls(data_dir, ffmpeg_bin)


CONFIG = PscPlotConfig._load()
