from lib.data.data_with_attrs import DataWithAttrs


class DataWorld:
    def __init__(self):
        self.datas: dict[str, DataWithAttrs] = {}
        self.active_key: str | None = None

    @property
    def active_data(self) -> DataWithAttrs | None:
        if self.active_key is None:
            return None
        return self.datas[self.active_key]
