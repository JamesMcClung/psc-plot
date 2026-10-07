import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass

from lib.data.data_world import DataWorld
from lib.parsing.parse_save import SaveSpec
from lib.plotting.plot import Plot
from lib.profiling.profiler import FINISH, profile_stage
from lib.run.usage_error import UsageError


class PlotAction(ABC):
    @abstractmethod
    def run(self, plot: Plot) -> None: ...


class ShowPlot(PlotAction):
    def run(self, plot: Plot) -> None:
        plot.show()


@dataclass(frozen=True)
class RenderPlot(PlotAction):
    """Renders every frame, or the first `max_frames`, offscreen and discards it, e.g. to profile a pipeline without showing or saving."""

    max_frames: int | None = None

    def run(self, plot: Plot) -> None:
        plot.render_offscreen(self.max_frames)


@dataclass(frozen=True)
class SavePlot(PlotAction):
    save: SaveSpec
    save_dpi: float | None
    default_stem: str

    def run(self, plot: Plot) -> None:
        with profile_stage(FINISH, exclusive=True):
            save_format = self.save.format
            if save_format not in plot.allowed_save_formats():
                if save_format is not None:
                    message = f"{save_format} is incompatible with the data; reverting to default ({plot.default_save_format()})"
                    warnings.warn(message)

                save_format = plot.default_save_format()

            path = self.save.resolve_path(self.default_stem, save_format)
            path.parent.mkdir(exist_ok=True, parents=True)
            plot.save_to_path(path, dpi=self.save_dpi)
            print(f"wrote to {path}")


@dataclass(frozen=True)
class DaskGraph:
    """Renders the dask graph of the pipeline's active data as SVG. Not a `PlotAction`: it must not build a plot."""

    save: SaveSpec
    show: bool
    default_stem: str

    def run(self, world: DataWorld) -> None:
        data = world.require_active_data()

        collections = data.dask_collections()
        if not collections:
            raise UsageError(f"--dask-graph requires dask-backed data; pipeline produced eager {type(data).__name__}")

        try:
            import graphviz  # noqa: F401
        except ImportError:
            raise UsageError("--dask-graph requires the 'graphviz' package; install with `pip install -e \".[dask-graph]\"`") from None

        import dask

        # save.format is ignored: the extension here is always .daskgraph.svg
        path = self.save.resolve_path(self.default_stem, "daskgraph.svg")
        path.parent.mkdir(exist_ok=True, parents=True)
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
