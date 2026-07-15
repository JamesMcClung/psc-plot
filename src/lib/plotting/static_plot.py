from pathlib import Path

import matplotlib.pyplot as plt

from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.plot import Plot, SaveFormat


class StaticPlot[Data: DataWithAttrs](Plot[Data]):
    def _get_initial_data(self) -> DataWithAttrs:
        return self.data

    def show(self):
        self._initialize()
        plt.show()

    def allowed_save_formats(self) -> list[SaveFormat]:
        return ["png"]

    def save_to_path(self, path: Path, *, dpi: float | None = None):
        self._initialize()
        self.fig.savefig(path, dpi=dpi or "figure")
