from .adaptor import Adaptor


class Pipeline(Adaptor):
    def __init__(self, *adaptors: Adaptor):
        self.adaptors = list(adaptors)

    def get_name_fragments(self) -> list[str]:
        return [fragment for adaptor in self.adaptors for fragment in adaptor.get_name_fragments()]

    def apply(self, data):
        for adaptor in self.adaptors:
            data = adaptor.apply(data)
        return data
