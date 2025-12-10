import typing
from abc import abstractmethod
from pathlib import Path

import matplotlib.pyplot as plt

from lib.data.data_with_attrs import DataWithAttrs
from lib.data.keys import SPATIAL_DIMS_KEY
from lib.plotting import plt_util
from lib.plotting.plot import Plot


class StaticPlot[Data: DataWithAttrs](Plot[Data]):
    def __init__(
        self,
        data: Data,
        *,
        scales: list[plt_util.Scale] = [],
        subplot_kw: dict[str, typing.Any] = {},
    ):
        super().__init__(data)
        self.spatial_dims: list[str] = self.data.attrs[SPATIAL_DIMS_KEY]
        self.scales = scales + ["linear"] * (1 + len(self.spatial_dims) - len(scales))

        self.fig, self.ax = plt.subplots(subplot_kw=subplot_kw)
        self._initialized = False

    @abstractmethod
    def _init_fig(self): ...

    def _initialize(self):
        if not self._initialized:
            self._init_fig()
            self._initialized = True

    def show(self):
        self._initialize()
        plt.show()

    def _get_save_ext(self):
        return ".png"

    def _save_to_path(self, path: Path):
        self._initialize()
        self.fig.savefig(path)
