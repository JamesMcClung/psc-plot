from dataclasses import dataclass

from lib.data.data_with_attrs import DataWithAttrs


@dataclass(frozen=True)
class DataWorld:
    datas: dict[str, DataWithAttrs] = []
    active_key: str | None = None

    def __post_init__(self):
        assert self.active_key is None or self.active_key in self.datas

    @property
    def active_data(self) -> DataWithAttrs | None:
        if self.active_key is None:
            return None
        return self.datas[self.active_key]
