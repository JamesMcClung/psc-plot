from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

from lib.config import PscPlotConfig
from lib.data.compile import compile_plot_node
from lib.parsing.parse import parse_args
from lib.plotting.plot import SaveFormat

_TESTS_DIR = Path(__file__).parent
_DATA_DIR = _TESTS_DIR / "data"
CONFIG_2D = PscPlotConfig(data_dir=_DATA_DIR / "test-2d")

matplotlib.use("Agg")


def make_plot(args_list: list[str], data_dir: str = "test-2d"):
    """Parse CLI args, run the full pipeline, and return the initialized figure."""
    args = parse_args(args_list)
    plot = compile_plot_node(args, PscPlotConfig(data_dir=_DATA_DIR / data_dir)).pull()
    plot._initialize()
    return plot.fig


def make_save(args_list: list[str], save_dir: Path, format: SaveFormat, data_dir: str = "test-2d"):
    """Parse CLI args, run the full pipeline, and save to save_dir. Returns the output file path."""
    args = parse_args(args_list)
    node = compile_plot_node(args, PscPlotConfig(data_dir=_DATA_DIR / data_dir))
    plot = node.pull()
    save_dir.mkdir(exist_ok=True)
    path = save_dir / f"{node.get_save_file_stem()}.{format}"
    plot.save_to_path(path)
    return path


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")
