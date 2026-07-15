from abc import ABC, abstractmethod
from functools import cache

from lib.data.adaptor import Adaptor
from lib.data.data_world import DataWorld
from lib.data.loader import Loader
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook
from lib.plotting.plot import Plot


class DataProcessingNode[D](ABC):
    def __init__(self, name_fragments: list[str]):
        self.name_fragments = name_fragments

    @abstractmethod
    def pull(self) -> D: ...


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
        return DataWorld(self.loader.get_data(), self.loader.active_key)


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
