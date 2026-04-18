import os
from pathlib import Path

# Must set env var and backend before any lib imports
_TESTS_DIR = Path(__file__).parent
_DATA_DIR = _TESTS_DIR / "data"
os.environ["PSC_PLOT_DATA_DIR"] = str(_DATA_DIR / "test-2d")
os.environ["PSC_PLOT_DASK_NUM_WORKERS"] = "1"

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from lib.config import CONFIG
from lib.parsing.args import Args
from lib.parsing.parse import _get_parser
from lib.plotting.plot import SaveFormat


def make_plot(args_list: list[str], data_dir: str | None = None):
    """Parse CLI args, run the full pipeline, and return the initialized figure."""
    if data_dir is not None:
        original_dir = CONFIG.data_dir
        CONFIG.data_dir = _DATA_DIR / data_dir

    try:
        parser = _get_parser()
        args = parser.parse_args(args_list, namespace=Args())
        plot = args.get_animation()
        plot._initialize()
        return plot.fig
    finally:
        if data_dir is not None:
            CONFIG.data_dir = original_dir


def make_save(args_list: list[str], save_dir: Path, format: SaveFormat, data_dir: str | None = None):
    """Parse CLI args, run the full pipeline, and save to save_dir. Returns the output file path."""
    if data_dir is not None:
        original_dir = CONFIG.data_dir
        CONFIG.data_dir = _DATA_DIR / data_dir

    try:
        parser = _get_parser()
        args = parser.parse_args(args_list, namespace=Args())
        plot = args.get_animation()
        save_dir.mkdir(exist_ok=True)
        plot.save(save_dir, format=format)

        name = "-".join(plot.data.metadata.name_fragments) + "." + format
        return save_dir / name
    finally:
        if data_dir is not None:
            CONFIG.data_dir = original_dir


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")
