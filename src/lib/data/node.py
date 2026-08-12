import sys
import warnings
from abc import ABC, abstractmethod
from functools import cache
from pathlib import Path

from lib import file_util
from lib.config import PscPlotConfig
from lib.data.adaptor import Adaptor
from lib.data.data_world import DataWorld
from lib.parsing.parse_save import SaveSpec
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook
from lib.plotting.plot import Plot


class DataProcessingNode[D](ABC):
    def __init__(self, name_fragments: list[str]):
        self.name_fragments = name_fragments

    @abstractmethod
    def pull(self) -> D: ...

    def get_save_file_stem(self) -> str:
        stem = "-".join(self.name_fragments)
        stem = file_util.sanitize_stem(stem)
        return stem


class AdaptorNode(DataProcessingNode[DataWorld]):
    def __init__(self, input_node: DataProcessingNode[DataWorld], adaptor: Adaptor):
        super().__init__(input_node.name_fragments + adaptor.get_name_fragments())
        self.input_node = input_node
        self.adaptor = adaptor

    @cache
    def pull(self) -> DataWorld:
        return self.adaptor.apply_world(self.input_node.pull())


class RootNode(DataProcessingNode[DataWorld]):
    def __init__(self, config: PscPlotConfig):
        super().__init__([])
        self.config = config

    def pull(self) -> DataWorld:
        return DataWorld(config=self.config)


class PlotNode(DataProcessingNode[Plot]):
    def __init__(self, input_node: DataProcessingNode[DataWorld], hooks: list[Hook]):
        super().__init__(input_node.name_fragments + [frag for hook in hooks for frag in hook.get_name_fragments()])
        self.input_node = input_node
        self.hooks = hooks

    @cache
    def pull(self) -> Plot:
        world = self.input_node.pull()
        plot = get_plot(world)

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
        save: SaveSpec,
        save_dpi: float | None,
    ):
        super().__init__(input_node.name_fragments)
        self.input_node = input_node
        self.save = save
        self.save_dpi = save_dpi

    def pull(self) -> None:
        plot = self.input_node.pull()

        save_format = self.save.format
        if save_format not in plot.allowed_save_formats():
            if save_format is not None:
                message = f"{save_format} is incompatible with the data; reverting to default ({plot.default_save_format()})"
                warnings.warn(message)

            save_format = plot.default_save_format()

        save_dir = self.save.dir or Path(".")
        save_dir.mkdir(exist_ok=True, parents=True)
        path = save_dir / f"{self.save.name or self.get_save_file_stem()}.{save_format}"
        plot.save_to_path(path, dpi=self.save_dpi)
        print(f"wrote to {path}")


class DaskGraphNode(DataProcessingNode[None]):
    def __init__(
        self,
        input_node: DataProcessingNode[DataWorld],
        *,
        save: SaveSpec | None,
        show: bool,
    ):
        super().__init__(input_node.name_fragments)
        self.input_node = input_node
        self.save = save or SaveSpec()
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

        # save.format is ignored: the extension here is always .daskgraph.svg
        save_dir = self.save.dir or Path.cwd()
        save_dir.mkdir(exist_ok=True, parents=True)
        path = save_dir / f"{self.save.name or self.get_save_file_stem()}.daskgraph.svg"
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
