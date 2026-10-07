from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

from lib.config import PscPlotConfig
from lib.parsing.parse import parse_args
from lib.plotting.plot import SaveFormat
from lib.run.compile import compile_plot_pipeline

_TESTS_DIR = Path(__file__).parent
_DATA_DIR = _TESTS_DIR / "data"
CONFIG_2D = PscPlotConfig.create_minimal(data_root=_DATA_DIR / "test-2d")
CONFIG_3D = PscPlotConfig.create_minimal(data_root=_DATA_DIR / "test-3d")

matplotlib.use("Agg")


def write_registry(registries_dir: Path, files: dict[str, str]) -> PscPlotConfig:
    """Write `{stem: yaml_text}` registry files and return a test-2d config that uses only them."""
    paths = []
    for stem, text in files.items():
        path = registries_dir / f"{stem}.yml"
        path.write_text(text)
        paths.append(str(path))
    return PscPlotConfig.create_minimal(data_root=CONFIG_2D.data_root, registries_use_defaults=False, registry_patterns=paths)


def make_plot(args_list: list[str], data_dir: str = "test-2d"):
    """Parse CLI args, run the full pipeline, and return the initialized figure."""
    args = parse_args(args_list)
    plot = compile_plot_pipeline(args, PscPlotConfig.create_minimal(data_root=_DATA_DIR / data_dir)).run_plot()
    plot._initialize()
    return plot.fig


def make_save(args_list: list[str], save_dir: Path, format: SaveFormat, data_dir: str = "test-2d"):
    """Parse CLI args, run the full pipeline, and save to save_dir. Returns the output file path."""
    args = parse_args(args_list)
    pipeline = compile_plot_pipeline(args, PscPlotConfig.create_minimal(data_root=_DATA_DIR / data_dir))
    plot = pipeline.run_plot()
    save_dir.mkdir(exist_ok=True)
    path = save_dir / f"{pipeline.get_save_file_stem()}.{format}"
    plot.save_to_path(path)
    return path


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")
