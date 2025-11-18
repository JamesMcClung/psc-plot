import itertools

from .adaptor import Adaptor


class Pipeline(Adaptor):
    def __init__(self, *adaptors: Adaptor):
        self.adaptors = list(adaptors)
        self._validate()

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

    def _validate(self):
        if not self.adaptors:
            raise ValueError("a pipeline must contain at least one adaptor")

        internal_output_type = self.adaptors[0].get_output_data_type()
        for i, adaptor in itertools.islice(enumerate(self.adaptors), 1, None):
            next_input_type = adaptor.get_input_data_type()
            if not issubclass(internal_output_type, next_input_type):
                raise ValueError(f"broken pipeline: adaptor {self.adaptors[i-1]} emits type {internal_output_type.__name__}, but feeds into adaptor {adaptor} which accepts {next_input_type.__name__}")
            internal_output_type = adaptor.get_output_data_type()
