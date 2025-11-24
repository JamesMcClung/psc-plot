import itertools
import typing

from .adaptor import Adaptor
from .compatability import require_compatible


class Pipeline(Adaptor):
    def __init__(self, *adaptors: Adaptor):
        self.adaptors = list(adaptors)

        for producer, consumer in itertools.pairwise(self.adaptors):
            require_compatible(producer, consumer)

    def get_name_fragments(self) -> list[str]:
        return [fragment for adaptor in self.adaptors for fragment in adaptor.get_name_fragments()]

    def apply(self, data):
        for adaptor in self.adaptors:
            data = adaptor.apply(data)
        return data

    def get_input_data_type(self) -> type:
        if not self.adaptors:
            return typing.Any
        return self.adaptors[0].get_input_data_type()

    def get_output_data_type(self) -> type:
        if not self.adaptors:
            return typing.Any
        return self.adaptors[-1].get_output_data_type()
