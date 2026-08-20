from matplotlib.figure import Figure

from lib.plotting.plot_info import PlotInfo

type AxesIdx = tuple[int, int]


class Grid:
    def __init__(self, fig: Figure, infos: list[PlotInfo]):
        self.fig = fig
        self.infos: dict[AxesIdx, list[PlotInfo]] = {}
        for info in infos:
            self.infos.setdefault(info.axes_index, []).append(info)

        self.ncols = max(idx[0] for idx in self.infos)
        self.nrows = max(idx[1] for idx in self.infos)
