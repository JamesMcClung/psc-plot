from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.transforms import ScaledTranslation

from lib.plotting import plt_util
from lib.plotting.labeler import SubjectLabeler
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
        h_pad = layout_engine.get()["h_pad"]
        layout_engine.set(h_pad=0.0, hspace=0.0)
        self._restore_vertical_figure_padding(h_pad)

        # Nothing may stick out past the shared edges either, or the space comes right back. The axes above
        # keep their bottom tick, its label tucked up out of the way; the axes below drop their top one, whose
        # label would otherwise crowd it.
        for col in self.contiguous_cols():
            for above, below in zip(col[:-1], col[1:]):
                above.mark_y_end_flush("lower")
                below.mark_y_end_flush("upper")
                below.prune_y_ticks("upper")

        # The bottom of each column follows the same rule as the edges within it, so that every axes in the
        # column reads the same way.
        for col in self.contiguous_cols():
            if len(col) > 1:
                col[-1].mark_y_end_flush("lower")

        # Sharing took the ticks off every edge but the bottom of each column, which leaves the axes above
        # it with nothing to read positions off. That bottom edge keeps its outward ticks too, beside its labels.
        for col in self.contiguous_cols():
            if len(col) > 1:
                for panel in col:
                    panel.add_interior_x_ticks({"lower", "upper"})

    def _restore_vertical_figure_padding(self, h_pad: float):
        """Put back the padding above and below the figure that zeroing `h_pad` took with it.

        `h_pad` is the padding at the edges of the figure as well as the floor on the gaps between
        axes, so the only way to keep one is to lay the whole figure out in a shorter rectangle.
        """
        pad = h_pad / self.fig.get_figheight()  # h_pad is in inches, the rectangle in figure fractions

        layout_engine = self.fig.get_layout_engine()
        assert layout_engine is not None
        layout_engine.set(rect=(0.0, pad, 1.0, 1.0 - 2 * pad))

        # The suptitle sits outside that rectangle: the engine puts it h_pad below the top of the
        # figure itself, which is now flush against it. Carrying the offset on its transform keeps it
        # clear of the edge, and leaves the engine still reserving exactly its height below it.
        self.suptitle.set_transform(self.fig.transSubfigure + ScaledTranslation(0.0, -h_pad, self.fig.dpi_scale_trans))

    def tuck_y_tick_labels(self):
        """Pull y tick labels back inside their axes wherever they overhang an edge that has to sit flush.

        Has to run after everything else that affects the layout, since it measures the labels where they
        were last drawn -- and again every frame, since the ticks move with the bounds.
        """
        renderer = self.fig.canvas.get_renderer()

        for panel in self.panels.values():
            panel.tuck_y_tick_labels(renderer)

    def update_interior_x_ticks(self):
        """Has to run every frame, since the tick locations follow the bounds and the colors the data."""
        for panel in self.panels.values():
            panel.update_interior_x_ticks()

    def right_align_cbar_labels(self):
        """Line up the right edges of the colorbar labels down each column, where matplotlib would line up
        none of their edges: it starts each label just past its own bar's tick labels, however wide those are.

        Only moves labels rightward, up to the right edge of the one that already reached furthest, so it
        doesn't change how much room constrained layout reserves for them. Has to run after everything else
        that affects the layout, and again every frame, for the same reasons as `tuck_y_tick_labels`.
        """
        renderer = self.fig.canvas.get_renderer()

        for col in self.contiguous_cols():
            cbars = [cbar for panel in col for cbar in panel.colorbars]
            if len(cbars) < 2:
                continue

            right = max(plt_util.get_default_cbar_label_left(cbar, renderer) + cbar.ax.yaxis.label.get_window_extent(renderer).width for cbar in cbars)

            for cbar in cbars:
                # A vertical colorbar's label reads bottom to top, so its bottom is its right edge. The label is
                # pinned at a fixed distance from the bar, rather than at a fraction of the bar's width: the bar
                # can still change size when the figure is next laid out (its width follows its height), but
                # the tick labels that distance was measured from won't.
                offset = (right - cbar.ax.get_window_extent(renderer).x1) / self.fig.dpi
                cbar.ax.yaxis.label.set_va("bottom")
                cbar.ax.yaxis.set_label_coords(1.0, 0.5, transform=cbar.ax.transAxes + ScaledTranslation(offset, 0.0, self.fig.dpi_scale_trans))

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
        self.tuck_y_tick_labels()
        self.right_align_cbar_labels()
