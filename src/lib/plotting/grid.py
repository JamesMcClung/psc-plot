from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.plotting.labeler import SubjectLabeler
from lib.plotting.panel import Panel
from lib.plotting.plot_info import PlotInfo

type AxesIdx = tuple[int, int]


def _flatten_idx(axes_idx: AxesIdx, ncols: int) -> int:
    return ncols * (axes_idx[1] - 1) + axes_idx[0]


class Grid:
    def __init__(self, fig: Figure, infos: list[PlotInfo]):
        self.fig = fig
        self.infos: dict[AxesIdx, list[PlotInfo]] = {}
        self.panels: dict[AxesIdx, Panel] = {}
        self.suptitle_labeler: SubjectLabeler | None = None

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

    def set_panel(self, loc: AxesIdx, panel: Panel):
        self.panels[loc] = panel

    def wire_suptitle(self):
        if len(self.panels) >= 2:
            self.suptitle_labeler = SubjectLabeler(self.fig.suptitle("").set_text)
            for panel in self.panels.values():
                for subject_labeler in panel.get_subject_labelers(toplevel_only=True):
                    self.suptitle_labeler.add_child(subject_labeler)

            self.suptitle_labeler.update()

    def update(self):
        for panel in self.panels.values():
            panel.update()
        if self.suptitle_labeler:
            self.suptitle_labeler.update()
