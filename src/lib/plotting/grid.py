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
        # Each column splits into stacks: runs of panels that share an x axis all the way down.
        stacks_per_col: list[list[list[Panel]]] = []
        for col in self.contiguous_cols():
            stacks = [[col[0]]]
            for above, below in zip(col[:-1], col[1:]):
                if above.try_share_x_axis(below):
                    stacks[-1].append(below)
                else:
                    stacks.append([below])
            stacks_per_col.append(stacks)

        if any(len(stack) > 1 for stacks in stacks_per_col for stack in stacks):
            self._remove_vertical_space(stacks_per_col)

    def _remove_vertical_space(self, stacks_per_col: list[list[list[Panel]]]):
        """Push the panels of each stack flush together, keeping the usual space between stacks."""
        # Constrained layout floors the gap between axes at h_pad, so zeroing hspace alone
        # isn't enough. Both are figure-wide, so the padding between stacks has to be put back.
        layout_engine = self.fig.get_layout_engine()
        assert layout_engine is not None
        h_pad = layout_engine.get()["h_pad"]
        layout_engine.set(h_pad=0.0, hspace=0.0)
        self._restore_vertical_figure_padding(h_pad)

        for stacks in stacks_per_col:
            # h_pad is the padding around each axes, so each side of the gap gets it back.
            for upper, lower in zip(stacks[:-1], stacks[1:]):
                upper[-1].pad_y_end("lower", h_pad * 72)  # h_pad is in inches, the pad in points
                lower[0].pad_y_end("upper", h_pad * 72)

        stacks = [stack for stacks in stacks_per_col for stack in stacks if len(stack) > 1]
        for stack in stacks:
            # Nothing may stick out past the shared edges, or the space comes right back. The axes above keep
            # their bottom tick, its label tucked up; the axes below drop their top one, which would crowd it.
            for above, below in zip(stack[:-1], stack[1:]):
                above.flush_y_ends.add("lower")
                below.flush_y_ends.add("upper")
                below.prune_y_ticks("upper")

            # The stack's bottom follows the same rule, so that every axes in it reads the same way.
            stack[-1].flush_y_ends.add("lower")

            # Sharing took the ticks off every edge but the stack's bottom, so give each axes its own.
            for panel in stack:
                panel.add_interior_x_ticks()

    def _restore_vertical_figure_padding(self, h_pad: float):
        """Put back the padding above and below the figure that zeroing `h_pad` took with it, by laying the
        figure out in a shorter rectangle (`h_pad` is both that padding and the floor on gaps between axes)."""
        pad = h_pad / self.fig.get_figheight()  # h_pad is in inches, the rectangle in figure fractions

        layout_engine = self.fig.get_layout_engine()
        assert layout_engine is not None
        layout_engine.set(rect=(0.0, pad, 1.0, 1.0 - 2 * pad))

        # The engine puts the suptitle h_pad below the figure's top, now zero; offset it back down.
        self.suptitle.set_transform(self.fig.transSubfigure + ScaledTranslation(0.0, -h_pad, self.fig.dpi_scale_trans))

    def tuck_y_tick_labels(self):
        """Pull y tick labels back inside their axes wherever they overhang an edge that has to sit flush."""
        renderer = self.fig.canvas.get_renderer()

        for panel in self.panels.values():
            panel.tuck_y_tick_labels(renderer)

    def update_interior_x_ticks(self):
        for panel in self.panels.values():
            panel.update_interior_x_ticks()

    def right_align_cbar_labels(self):
        """Line up the right edges of the colorbar labels down each column, where matplotlib would line up
        none of their edges: it starts each label just past its own bar's tick labels, however wide those are.

        Only moves labels rightward, up to the right edge of the one that already reached furthest, so it
        doesn't change how much room constrained layout reserves for them.
        """
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

    def adjust_to_last_draw(self):
        """Steps that measure where things were last drawn, so they must run after a layout, after everything
        else that affects it -- and again every frame, since what they measure moves with the bounds."""
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
        self.adjust_to_last_draw()
