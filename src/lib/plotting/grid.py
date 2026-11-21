from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.figure import Figure

from lib.plotting import plt_util, tick_labels
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
        self.flush_col_boundaries: set[int] = set()
        """Columns `c` whose panels sit flush against those of column `c + 1`, sharing their y axes."""

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

    def share_y_axes_horizontally(self, dpi: float):
        """Put panels side by side along each row where they can share a y axis. Plot edges line up across the
        whole grid, so a column boundary is flush only if every row with panels on both sides of it can share
        there. Sizes come first: plot heights must already match."""
        sizes = {loc: auto_plot_size(infos, dpi) for loc, infos in self.infos.items()}

        for col in range(1, self.ncols):
            pairs = [(self.panels[(col, row)], self.panels[(col + 1, row)], (col, row)) for row in range(1, self.nrows + 1) if (col, row) in self.panels and (col + 1, row) in self.panels]
            if not pairs:
                continue
            if all(left.can_share_y_axis(right) and sizes_close(sizes[loc][1], sizes[(loc[0] + 1, loc[1])][1], dpi) for left, right, loc in pairs):
                for left, right, _ in pairs:
                    left.share_y_axis(right)
                self.flush_col_boundaries.add(col)

    def separate_junction_labels(self, renderer: RendererBase):
        """Where panels sit flush, hide the label of the panel below (or right) nearest the edge if it crowds its
        neighbor's."""
        for panel in self.panels.values():
            if below := panel.shared_x_below:
                for above_ax, below_ax in zip(panel.axes, below.axes):  # main axes, and twins if both have one
                    tick_labels.separate_junction_labels(above_ax.yaxis, below_ax.yaxis, renderer)
            if right := panel.shared_y_right:
                tick_labels.separate_junction_labels(panel.axes[0].xaxis, right.axes[0].xaxis, renderer)

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
        renderer = self.fig.canvas.get_renderer()
        for panel in self.panels.values():
            panel.tuck_tick_labels(renderer)
        self.separate_junction_labels(renderer)
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

    def update_label_texts(self):
        """`update_labels`, but leaving the legends be: cheap enough to run for every frame up front."""
        for panel in self.panels.values():
            panel.update_label_texts()

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
