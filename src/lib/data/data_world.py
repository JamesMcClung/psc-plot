from __future__ import annotations

from dataclasses import KW_ONLY, dataclass, field, replace

from lib.config import PscPlotConfig
from lib.data.data_with_attrs import DataWithAttrs
from lib.data.plot_target import PlotTarget
from lib.file_util import Prepath


@dataclass(frozen=True)
class DataWorld:
    # TODO python 3.15: make frozendict
    datas: dict[Prepath, DataWithAttrs] = field(default_factory=dict)
    active_prepath: Prepath | None = None
    _: KW_ONLY
    plot_targets: list[PlotTarget] = field(default_factory=list)
    config: PscPlotConfig = field(default_factory=PscPlotConfig.from_env)

    def __post_init__(self):
        assert self.active_prepath is None or self.active_prepath in self.datas

    @property
    def active_data(self) -> DataWithAttrs | None:
        if self.active_prepath is None:
            return None
        return self.datas[self.active_prepath]

    def with_active(
        self,
        *,
        data: DataWithAttrs | None = None,
        prepath: Prepath | None = None,
    ) -> DataWorld:
        if data is None:
            return replace(self, active_prepath=prepath)

        prepath = prepath or self.active_prepath
        assert prepath is not None

        new_datas = self.datas.copy()
        new_datas[prepath] = data
        return replace(self, datas=new_datas, active_prepath=prepath)

    def with_data(
        self,
        prepath: Prepath,
        data: DataWithAttrs,
    ) -> DataWorld:
        return replace(self, datas=self.datas | {prepath: data})
