from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.plotting import plt_util
from lib.plotting.labeler import SubjectLabeler
from lib.plotting.layout.auto_size import auto_plot_size
from lib.plotting.layout.geometry import sizes_close
from lib.plotting.panel import Panel
from lib.plotting.plot_info import PlotInfo
from lib.plotting.style import scaled_font_size

type AxesIdx = tuple[int, int]


class Grid:
    def __init__(self, fig: Figure, infos: list[PlotInfo]):
        self.fig = fig
        self.infos: dict[AxesIdx, list[PlotInfo]] = {}
        self.panels: dict[AxesIdx, Panel] = {}
        self.suptitle = self.fig.suptitle("", fontsize=scaled_font_size("figure.titlesize"))
        self.suptitle_labeler = SubjectLabeler(self.suptitle.set_text)

        for info in infos:
            self.infos.setdefault(info.axes_index, []).append(info)

        self.ncols = max(idx[0] for idx in self.infos)
        self.nrows = max(idx[1] for idx in self.infos)

        self.flush_row_boundaries: set[int] = set()
        """Rows `r` whose panels sit flush against those of row `r + 1`, sharing their x axes."""

    def setup_ax(self, loc: AxesIdx) -> Axes:
        infos = self.infos[loc]
        projection = infos[0].projection
        for info in infos[1:]:
            if info.projection != projection:
                raise ValueError("incompatible plots (TODO: better error message)")
        return self.fig.add_axes((0.0, 0.0, 1.0, 1.0), projection=projection)  # the layout engine places it

    def set_panel(self, loc: AxesIdx, panel: Panel):
        if len(self.panels) == 1:
            first_panel = list(self.panels.values())[0]  # next() isn't typed for some reason
            self._wire_suptitle(first_panel)

        if len(self.panels) >= 1:
            self._wire_suptitle(panel)

        self.panels[loc] = panel

    def share_x_axes_vertically(self, dpi: float):
        """Stack panels down each column where they can share an x axis. Plot edges line up across the whole
        grid, so a row boundary is flush only if every column with panels on both sides of it can share there."""
        sizes = {loc: auto_plot_size(infos, dpi) for loc, infos in self.infos.items()}

        for row in range(1, self.nrows):
            pairs = [(self.panels[(col, row)], self.panels[(col, row + 1)], (col, row)) for col in range(1, self.ncols + 1) if (col, row) in self.panels and (col, row + 1) in self.panels]
            if not pairs:
                continue
            if all(above.can_share_x_axis(below) and sizes_close(sizes[loc][0], sizes[(loc[0], loc[1] + 1)][0], dpi) for above, below, loc in pairs):
                for above, below, _ in pairs:
                    above.share_x_axis(below)
                self.flush_row_boundaries.add(row)

        # The panel below drops its top y tick, so its label can't crowd the bottom one of the panel above.
        for col in self.contiguous_cols():
            for above, below in zip(col[:-1], col[1:]):
                if above.shares_x_with(below):
                    below.prune_y_ticks("upper")

    def stacks(self) -> list[list[Panel]]:
        """Each column's runs of panels that share an x axis all the way down, top to bottom."""
        stacks = []
        for col in self.contiguous_cols():
            stacks.append([col[0]])
            for above, below in zip(col[:-1], col[1:]):
                if above.shares_x_with(below):
                    stacks[-1].append(below)
                else:
                    stacks.append([below])
        return stacks

    def update_ticks(self):
        for panel in self.panels.values():
            panel.update_ticks()

    def adjust_to_draw(self):
        """Steps that measure where things were drawn. The layout engine runs them after each of its passes."""
        for panel in self.panels.values():
            panel.thin_crowded_ticks(self.fig.canvas.get_renderer())
        self.fig.draw_without_rendering()
        for panel in self.panels.values():
            panel.tuck_tick_labels(self.fig.canvas.get_renderer())
        for panel in self.panels.values():
            panel.update_cbar_bottom_texts()

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
        self.update_ticks()
        self.update_labels()
