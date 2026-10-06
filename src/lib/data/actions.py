import sys
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from lib.data.data_world import DataWorld
from lib.data.pipeline import Pipeline
from lib.parsing.parse_save import SaveSpec
from lib.plotting.plot import Plot
from lib.profiling.profiler import FINISH, profile_stage


class PlotAction(ABC):
    @abstractmethod
    def run(self, plot: Plot, pipeline: Pipeline) -> None: ...


class ShowPlot(PlotAction):
    def run(self, plot: Plot, pipeline: Pipeline) -> None:
        plot.show()


class RenderPlot(PlotAction):
    """Renders every frame offscreen and discards it, e.g. to profile a pipeline without showing or saving."""

    def run(self, plot: Plot, pipeline: Pipeline) -> None:
        plot.render_offscreen()


@dataclass(frozen=True)
class SavePlot(PlotAction):
    save: SaveSpec
    save_dpi: float | None

    def run(self, plot: Plot, pipeline: Pipeline) -> None:
        with profile_stage(FINISH, exclusive=True):
            save_format = self.save.format
            if save_format not in plot.allowed_save_formats():
                if save_format is not None:
                    message = f"{save_format} is incompatible with the data; reverting to default ({plot.default_save_format()})"
                    warnings.warn(message)

                save_format = plot.default_save_format()

            save_dir = self.save.dir or Path(".")
            save_dir.mkdir(exist_ok=True, parents=True)
            path = save_dir / f"{self.save.name or pipeline.get_save_file_stem()}.{save_format}"
            plot.save_to_path(path, dpi=self.save_dpi)
            print(f"wrote to {path}")


@dataclass(frozen=True)
class DaskGraph:
    """Renders the dask graph of the pipeline's active data as SVG. Not a `PlotAction`: it must not build a plot."""

    save: SaveSpec
    show: bool

    def run(self, world: DataWorld, pipeline: Pipeline) -> None:
        data = world.active_data

        collections = data.dask_collections()
        if not collections:
            print(
                f"error: --dask-graph requires dask-backed data; pipeline produced eager {type(data).__name__}",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            import graphviz  # noqa: F401
        except ImportError:
            print(
                "error: --dask-graph requires the 'graphviz' package; install with `pip install -e \".[dask-graph]\"`",
                file=sys.stderr,
            )
            sys.exit(1)

        import dask

        # save.format is ignored: the extension here is always .daskgraph.svg
        save_dir = self.save.dir or Path.cwd()
        save_dir.mkdir(exist_ok=True, parents=True)
        path = save_dir / f"{self.save.name or pipeline.get_save_file_stem()}.daskgraph.svg"
        # dask.visualize's optimize_graph flag only lowers legacy HLG collections
        # (e.g. dask Arrays), not new-style Expr ones (dask DataFrames) — without
        # pre-optimizing the latter, un-lowered nodes (e.g. Concat from dd.concat)
        # fail with NotImplementedError in _layer.
        collections = [c.optimize() if hasattr(c, "optimize") else c for c in collections]
        dask.visualize(*collections, filename=str(path), optimize_graph=True)
        print(f"wrote to {path}")

        if self.show:
            import webbrowser

            webbrowser.open(path.absolute().as_uri())
