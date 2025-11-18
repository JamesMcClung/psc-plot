import itertools

from ..data_handling import require_compatible
from .adaptor import Adaptor


class Pipeline(Adaptor):
    def __init__(self, *adaptors: Adaptor):
        self.adaptors = list(adaptors)

        if not self.adaptors:
            raise ValueError("a pipeline must contain at least one adaptor")

        for producer, consumer in itertools.pairwise(self.adaptors):
            require_compatible(producer, consumer)

    def get_name_fragments(self) -> list[str]:
        return [fragment for adaptor in self.adaptors for fragment in adaptor.get_name_fragments()]

    def apply(self, data):
        for adaptor in self.adaptors:
            data = adaptor.apply(data)
        return data

    def get_modified_var_name(self, dep_var_name: str) -> str:
        for adaptor in self.adaptors:
            dep_var_name = adaptor.get_modified_var_name(dep_var_name)
        return dep_var_name

    def get_input_data_type(self) -> type:
        return self.adaptors[0].get_input_data_type()

    def get_output_data_type(self) -> type:
        return self.adaptors[-1].get_output_data_type()
