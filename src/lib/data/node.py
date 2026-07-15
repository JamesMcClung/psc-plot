import sys
import warnings
from abc import ABC, abstractmethod
from functools import cache
from pathlib import Path

from lib.data.adaptor import Adaptor
from lib.data.data_world import DataWorld
from lib.data.loader import Loader
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook
from lib.plotting.plot import Plot, SaveFormat


class DataProcessingNode[D](ABC):
    def __init__(self, name_fragments: list[str]):
        self.name_fragments = name_fragments

    @abstractmethod
    def pull(self) -> D: ...

    def get_save_file_stem(self) -> str:
        return "-".join(self.name_fragments)


class AdaptorNode(DataProcessingNode[DataWorld]):
    def __init__(self, input_node: DataProcessingNode[DataWorld], adaptor: Adaptor):
        super().__init__(input_node.name_fragments + adaptor.get_name_fragments())
        self.input_node = input_node
        self.adaptor = adaptor

    @cache
    def pull(self) -> DataWorld:
        return self.adaptor.apply_world(self.input_node.pull())


class LoaderNode(DataProcessingNode[DataWorld]):
    def __init__(self, loader: Loader):
        super().__init__(loader.get_name_fragments())
        self.loader = loader

    @cache
    def pull(self) -> DataWorld:
        return DataWorld({self.loader.prefix: self.loader.get_data()}, self.loader.prefix)


class PlotNode(DataProcessingNode[Plot]):
    def __init__(self, input_node: DataProcessingNode[DataWorld], hooks: list[Hook]):
        super().__init__(input_node.name_fragments + [frag for hook in hooks for frag in hook.get_name_fragments()])
        self.input_node = input_node
        self.hooks = hooks

    @cache
    def pull(self) -> Plot:
        data = self.input_node.pull()
        plot = get_plot(data.active_data)

        for hook in self.hooks:
            plot.add_hook(hook)

        return plot


class ShowPlotNode(DataProcessingNode[None]):
    def __init__(self, input_node: DataProcessingNode[Plot]):
        super().__init__(input_node.name_fragments)
        self.input_node = input_node

    def pull(self) -> None:
        self.input_node.pull().show()


class SavePlotNode(DataProcessingNode[None]):
    def __init__(
        self,
        input_node: DataProcessingNode[Plot],
        *,
        save_dir: Path,
        save_format: SaveFormat | None,
        save_dpi: float,
    ):
        super().__init__(input_node.name_fragments)
        self.input_node = input_node
        self.save_dir = save_dir
        self.save_format = save_format
        self.save_dpi = save_dpi

    def pull(self) -> None:
        plot = self.input_node.pull()

        format = self.save_format
        if format not in plot.allowed_save_formats():
            if format is not None:
                message = f"{format} is incompatible with the data; reverting to default ({plot.default_save_format()})"
                warnings.warn(message)

            format = plot.default_save_format()

        if format == "mp4":
            from matplotlib import pyplot as plt

            from lib.config import CONFIG

            plt.rcParams["animation.ffmpeg_path"] = str(CONFIG.ffmpeg_bin)

        self.save_dir.mkdir(exist_ok=True, parents=True)
        path = self.save_dir / f"{self.get_save_file_stem()}.{format}"
        plot.save_to_path(path, dpi=self.save_dpi)
        print(f"wrote to {path}")


class DaskGraphNode(DataProcessingNode[None]):
    def __init__(
        self,
        input_node: DataProcessingNode[DataWorld],
        *,
        save_dir: Path | None,
        show: bool,
    ):
        super().__init__(input_node.name_fragments)
        self.input_node = input_node
        self.save_dir = save_dir or Path.cwd()
        self.show = show

    def pull(self) -> None:
        data = self.input_node.pull().active_data

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

        self.save_dir.mkdir(exist_ok=True, parents=True)
        path = self.save_dir / f"{self.get_save_file_stem()}.daskgraph.svg"
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
