from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.plotting.plot_info import PlotInfo

type AxesIdx = tuple[int, int]


def _flatten_idx(axes_idx: AxesIdx, ncols: int) -> int:
    return ncols * (axes_idx[1] - 1) + axes_idx[0]


class Grid:
    def __init__(self, fig: Figure, infos: list[PlotInfo]):
        self.fig = fig
        self.infos: dict[AxesIdx, list[PlotInfo]] = {}
        for info in infos:
            self.infos.setdefault(info.axes_index, []).append(info)

        self.ncols = max(idx[0] for idx in self.infos)
        self.nrows = max(idx[1] for idx in self.infos)

    def setup_ax(self, loc: AxesIdx) -> Axes:
        infos = self.infos[loc]
        projection = infos[0].projection
        for info in infos[1:]:
            if info.projection != projection:
                raise ValueError("incompatible plots (TODO: better error message)")
        return self.fig.add_subplot(self.nrows, self.ncols, _flatten_idx(loc, self.ncols), projection=projection)
