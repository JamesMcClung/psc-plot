from .adaptor import Adaptor


class Pipeline[Data](Adaptor[Data]):
    def __init__(self, *adaptors: Adaptor[Data]):
        self.adaptors = list(adaptors)

    def get_name_fragments(self) -> list[str]:
        return [fragment for adaptor in self.adaptors for fragment in adaptor.get_name_fragments()]

    def apply(self, data: Data) -> Data:
        for adaptor in self.adaptors:
            data = adaptor.apply(data)
        return data

    def get_modified_var_name(self, dep_var_name: str) -> str:
        for adaptor in self.adaptors:
            dep_var_name = adaptor.get_modified_var_name(dep_var_name)
        return dep_var_name
