from lib.data.data_with_attrs import DataWithAttrs


class DataWorld:
    def __init__(self):
        self.datas: dict[str, DataWithAttrs] = {}
        self.active_key: str | None = None
