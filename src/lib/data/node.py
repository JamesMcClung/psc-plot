from abc import ABC, abstractmethod
from functools import cache

from lib.data.adaptor import Adaptor
from lib.data.data_world import DataWorld
from lib.data.loader import Loader


class DataProcessingNode[D](ABC):
    @abstractmethod
    def pull(self) -> D: ...


class AdaptorNode(DataProcessingNode[DataWorld]):
    def __init__(self, adaptor: Adaptor, input_node: DataProcessingNode[DataWorld]):
        self.adaptor = adaptor
        self.input_node = input_node

    @cache
    def pull(self) -> DataWorld:
        return self.adaptor.apply_world(self.input_node.pull())


class LoaderNode(DataProcessingNode[DataWorld]):
    def __init__(self, loader: Loader):
        self.loader = loader

    @cache
    def pull(self) -> DataWorld:
        return DataWorld(self.loader.get_data(), self.loader.active_key)
