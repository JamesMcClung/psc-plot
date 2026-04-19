from pathlib import Path

import matplotlib.pyplot as plt

from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.plot import Plot, SaveFormat
from lib.plotting.renderer import Renderer


class StaticPlot[Data: DataWithAttrs](Plot[Data]):
    def __init__(self, renderer: Renderer[Data], data: Data):
        super().__init__(renderer, data)

        self.fig, self.ax = plt.subplots(subplot_kw=renderer.subplot_kw())
        self._initialized = False

    def _initialize(self):
        if self._initialized:
            return
        self._initialized = True

        init_data = self.renderer.make_init_data(self.fig, self.ax, self.data)
        self.pre_init_fig(init_data)
        self.renderer.init(self.fig, self.ax, self.data, self.data, init_data)
        self.post_init_fig(init_data)
        self.fig.tight_layout()

    def show(self):
        self._initialize()
        plt.show()

    def allowed_save_formats(self) -> list[SaveFormat]:
        return ["png"]

    def _save_to_path(self, path: Path):
        self._initialize()
        self.fig.savefig(path)
