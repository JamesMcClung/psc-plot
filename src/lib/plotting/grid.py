from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.plotting.labeler import SubjectLabeler
from lib.plotting.panel import Panel
from lib.plotting.plot_info import PlotInfo

type AxesIdx = tuple[int, int]


class Grid:
    def __init__(self, fig: Figure, infos: list[PlotInfo]):
        self.fig = fig
        self.infos: dict[AxesIdx, list[PlotInfo]] = {}
        self.panels: dict[AxesIdx, Panel] = {}
        self.suptitle_labeler = SubjectLabeler(self.fig.suptitle("").set_text)

        for info in infos:
            self.infos.setdefault(info.axes_index, []).append(info)

        self.ncols = max(idx[0] for idx in self.infos)
        self.nrows = max(idx[1] for idx in self.infos)
        self.gridspec = self.fig.add_gridspec(self.nrows, self.ncols)

    def setup_ax(self, loc: AxesIdx) -> Axes:
        infos = self.infos[loc]
        projection = infos[0].projection
        for info in infos[1:]:
            if info.projection != projection:
                raise ValueError("incompatible plots (TODO: better error message)")
        return self.fig.add_subplot(self.gridspec[loc[1] - 1, loc[0] - 1], projection=projection)

    def set_panel(self, loc: AxesIdx, panel: Panel):
        if len(self.panels) == 1:
            first_panel = list(self.panels.values())[0]  # next() isn't typed for some reason
            self._wire_suptitle(first_panel)

        if len(self.panels) >= 1:
            self._wire_suptitle(panel)

        self.panels[loc] = panel

    def share_x_axes_vertically(self):
        shared_all = True
        for col in self.contiguous_cols():
            for above, below in zip(col[:-1], col[1:]):
                shared_all &= above.try_share_axis(below, "x")

        if shared_all:
            self._remove_vertical_space()

    def _remove_vertical_space(self):
        # Constrained layout floors the gap between axes at h_pad, so zeroing hspace alone
        # isn't enough. Both are figure-wide, so this also closes gaps between any axes that
        # didn't end up sharing.
        layout_engine = self.fig.get_layout_engine()
        assert layout_engine is not None
        layout_engine.set(h_pad=0.0, hspace=0.0)

        # Nothing may stick out past the shared edges either, or the space comes right back.
        for col in self.contiguous_cols():
            for above, below in zip(col[:-1], col[1:]):
                above.prune_y_ticks("lower")
                below.prune_y_ticks("upper")

    def contiguous_cols(self) -> list[list[Panel]]:
        cols = []
        for x in range(1, self.ncols + 1):
            col = []
            for y in range(1, self.nrows + 1):
                if panel := self.panels.get((x, y)):
                    col.append(panel)
                elif col:
                    cols.append(col)
                    col = []
            if col:
                cols.append(col)
        return cols

    def _wire_suptitle(self, panel: Panel):
        for subject_labeler in panel.get_subject_labelers(toplevel_only=True):
            self.suptitle_labeler.add_child(subject_labeler)

    def update_labels(self):
        for panel in self.panels.values():
            panel.update_labels()

        if self.suptitle_labeler:
            self.suptitle_labeler.update()

    def update_data(self):
        for panel in self.panels.values():
            panel.update_data()

    def update_bounds(self):
        for panel in self.panels.values():
            panel.update_bounds()

    def update(self):
        self.update_data()
        self.update_bounds()
        self.update_labels()
