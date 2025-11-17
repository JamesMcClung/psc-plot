from .adaptor import Adaptor


class Pipeline[Data]:
    def __init__(self, *adaptors: Adaptor[Data]):
        self.adaptors = list(adaptors)

    def get_name_fragments(self) -> list[str]:
        name_fragments = [adaptor.get_name_fragment() for adaptor in self.adaptors]
        name_fragments = [frag for frag in name_fragments if frag]
        return name_fragments

    def apply(self, data: Data) -> Data:
        for adaptor in self.adaptors:
            data = adaptor.apply(data)
        return data

    def get_modified_var_name(self, dep_var_name: str) -> str:
        for adaptor in self.adaptors:
            dep_var_name = adaptor.get_modified_var_name(dep_var_name)
        return dep_var_name
