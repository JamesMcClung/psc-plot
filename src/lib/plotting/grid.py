from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.transforms import ScaledTranslation

from lib.plotting import plt_util
from lib.plotting.labeler import SubjectLabeler
from lib.plotting.layout.auto_size import auto_plot_size
from lib.plotting.layout.geometry import sizes_close
from lib.plotting.panel import Panel
from lib.plotting.plot_info import PlotInfo

type AxesIdx = tuple[int, int]


class Grid:
    def __init__(self, fig: Figure, infos: list[PlotInfo]):
        self.fig = fig
        self.infos: dict[AxesIdx, list[PlotInfo]] = {}
        self.panels: dict[AxesIdx, Panel] = {}
        self.suptitle = self.fig.suptitle("")
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

        for col in self.contiguous_cols():
            for above, below in zip(col[:-1], col[1:]):
                if not above.shares_x_with(below):
                    continue
                # The axes above keep their bottom tick, its label tucked up; the axes below drop their top one.
                above.flush_y_ends.add("lower")
                below.flush_y_ends.add("upper")
                below.prune_y_ticks("upper")

        for stack in self.stacks():
            if len(stack) > 1:
                stack[-1].flush_y_ends.add("lower")
                for panel in stack:
                    panel.add_interior_x_ticks()

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

    def tuck_y_tick_labels(self):
        renderer = self.fig.canvas.get_renderer()

        for panel in self.panels.values():
            panel.tuck_y_tick_labels(renderer)

    def update_interior_x_ticks(self):
        for panel in self.panels.values():
            panel.update_interior_x_ticks()

    def right_align_cbar_labels(self):
        """Line up the right edges of the colorbar labels down each column. Only moves labels rightward, up to the
        furthest one, so constrained layout doesn't reserve any more room for them."""
        renderer = self.fig.canvas.get_renderer()

        for col in self.contiguous_cols():
            cbars = [cbar for panel in col for cbar in panel.colorbars]
            if len(cbars) < 2:
                continue

            right = max(plt_util.get_default_cbar_label_left(cbar, renderer) + cbar.ax.yaxis.label.get_window_extent(renderer).width for cbar in cbars)

            for cbar in cbars:
                # The label reads bottom to top, so its bottom is its right edge. Pinned in fixed units, not
                # axes fractions, since the bar can still resize at the next layout.
                offset = (right - cbar.ax.get_window_extent(renderer).x1) / self.fig.dpi
                cbar.ax.yaxis.label.set_va("bottom")
                cbar.ax.yaxis.set_label_coords(1.0, 0.5, transform=cbar.ax.transAxes + ScaledTranslation(offset, 0.0, self.fig.dpi_scale_trans))

    def adjust_to_draw(self):
        """Steps that measure where things were drawn. The layout engine runs them after each of its passes."""
        self.tuck_y_tick_labels()
        self.right_align_cbar_labels()

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
        self.update_interior_x_ticks()
        self.update_labels()
