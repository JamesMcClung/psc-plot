from .adaptor import Adaptor


class Pipeline(Adaptor):
    def __init__(self, *adaptors: Adaptor):
        self.adaptors = list(adaptors)

    def apply(self, data):
        for adaptor in self.adaptors:
            data = adaptor.apply(data)
        return data
