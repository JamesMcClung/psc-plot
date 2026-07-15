from abc import ABC, abstractmethod
from functools import cache

from lib.data.adaptor import Adaptor
from lib.data.data_world import DataWorld
from lib.data.loader import Loader


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
