from dataclasses import dataclass, field

from lib.data.data_with_attrs import DataWithAttrs


@dataclass(frozen=True)
class DataWorld:
    # TODO python 3.15: make frozendict
    datas: dict[str, DataWithAttrs] = field(default_factory=dict)
    active_key: str | None = None

    def __post_init__(self):
        assert self.active_key is None or self.active_key in self.datas

    @property
    def active_data(self) -> DataWithAttrs | None:
        if self.active_key is None:
            return None
        return self.datas[self.active_key]

    def with_active_data(self, new_active_data: DataWithAttrs, new_key: str | None = None) -> DataWorld:
        new_key = new_key or self.active_key
        assert new_key is not None
        new_datas = self.datas.copy()
        new_datas[new_key] = new_active_data
        return DataWorld(new_datas, new_key)
