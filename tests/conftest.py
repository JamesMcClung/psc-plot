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
from lib.data.compile import compile_plot_node
from lib.parsing.parse import get_parsed_args
from lib.plotting.plot import SaveFormat


def make_plot(args_list: list[str], data_dir: str | None = None):
    """Parse CLI args, run the full pipeline, and return the initialized figure."""
    if data_dir is not None:
        original_dir = CONFIG.data_dir
        CONFIG.data_dir = _DATA_DIR / data_dir

    try:
        args = get_parsed_args(args_list)
        plot = compile_plot_node(args).pull()
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
        args = get_parsed_args(args_list)
        node = compile_plot_node(args)
        plot = node.pull()
        save_dir.mkdir(exist_ok=True)
        path = save_dir / f"{node.get_save_file_stem()}.{format}"
        plot.save_to_path(path)
        return path
    finally:
        if data_dir is not None:
            CONFIG.data_dir = original_dir


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")
