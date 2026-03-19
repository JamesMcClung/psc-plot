import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

_ROOT_DATA_PATH_ENV_VAR_NAME = "PSC_PLOT_ROOT_DATA_PATH"


@dataclass
class PscPlotConfig:
    data_dir: Path

    @classmethod
    def _load(cls) -> Self:
        data_dir = os.environ.get(_ROOT_DATA_PATH_ENV_VAR_NAME)
        if not data_dir:
            message = f"Path to data not specified. Set the {_ROOT_DATA_PATH_ENV_VAR_NAME} environment variable to specify."
            raise RuntimeError(message)

        return cls(data_dir)


CONFIG = PscPlotConfig._load()
