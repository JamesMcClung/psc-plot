from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.figure import Figure

from lib.plotting import plt_util, tick_labels
from lib.plotting.labeler import SharedColorbarLabel, SubjectLabeler, UnitLabeler
from lib.plotting.layout.auto_size import auto_plot_sizes, is_aspect_locked
from lib.plotting.layout.colorbars import CellModel, ColorbarAssignment, GridModel, assign_colorbars
from lib.plotting.layout.geometry import sizes_close
from lib.plotting.layout.options import LayoutOptions
from lib.plotting.panel import Panel, color_key
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

    def _sizes_stay_matched(self, a: AxesIdx, b: AxesIdx, options: LayoutOptions) -> bool:
        """Whether a fixed `--figsize` side scales `a` and `b` alike: it scales an aspect-locked plot area in both
        directions and any other in one, so with a fixed side they must both be locked or both not."""
        fixed = options.figsize.width is not None or options.figsize.height is not None
        return not fixed or is_aspect_locked(self.infos[a]) == is_aspect_locked(self.infos[b])

    def share_x_axes_vertically(self, options: LayoutOptions):
        """Stack panels down each column where they can share an x axis. Plot edges line up across the whole
        grid, so a row boundary is flush only if every column with panels on both sides of it can share there."""
        dpi = options.dpi
        sizes = auto_plot_sizes(self.infos, dpi)

        for row in range(1, self.nrows):
            pairs = [(self.panels[(col, row)], self.panels[(col, row + 1)], (col, row)) for col in range(1, self.ncols + 1) if (col, row) in self.panels and (col, row + 1) in self.panels]
            if not pairs:
                continue
            if all(above.can_share_x_axis(below) and sizes_close(sizes[loc][0], sizes[(loc[0], loc[1] + 1)][0], dpi) and self._sizes_stay_matched(loc, (loc[0], loc[1] + 1), options) for above, below, loc in pairs):
                for above, below, _ in pairs:
                    above.share_x_axis(below)
                self.flush_row_boundaries.add(row)

    def _col_pairs(self, col: int) -> list[tuple[AxesIdx, AxesIdx]]:
        return [((col, row), (col + 1, row)) for row in range(1, self.nrows + 1) if (col, row) in self.panels and (col + 1, row) in self.panels]

    def _shareable_col_boundaries(self, options: LayoutOptions) -> set[int]:
        """Columns whose panels could sit flush against the next column's, sharing y axes, colorbars aside. Plot
        edges line up across the whole grid, so every row with panels on both sides must be able to share, and
        plot heights must already match, and stay matched under a fixed `--figsize` side."""
        dpi = options.dpi
        sizes = auto_plot_sizes(self.infos, dpi)
        shareable = set()
        for col in range(1, self.ncols):
            pairs = self._col_pairs(col)
            # A panel with several color quantities needs a vertical bar for each, so it sits apart from its neighbors.
            if pairs and all(not self.panels[left].has_mixed_colors() and not self.panels[right].has_mixed_colors() and self.panels[left].can_share_y_axis(self.panels[right]) and sizes_close(sizes[left][1], sizes[right][1], dpi) and self._sizes_stay_matched(left, right, options) for left, right in pairs):
                shareable.add(col)
        return shareable

    def _x_stacks(self) -> list[list[AxesIdx]]:
        """Each column's runs of panels that share an x axis all the way down, top to bottom."""
        stacks = []
        for loc in sorted(self.panels, key=lambda loc: (loc[0], loc[1])):
            above = self.panels.get((loc[0], loc[1] - 1))
            if above is not None and above.shared_x_below is self.panels[loc]:
                stacks[-1].append(loc)
            else:
                stacks.append([loc])
        return stacks

    def arrange_colorbars(self, options: LayoutOptions):
        """Decide which colorbars the images get, and which column boundaries sit flush sharing y axes (they
        constrain each other: see `layout.colorbars`); then share those y axes and make those colorbars. Call
        after `share_x_axes_vertically`."""
        model = GridModel({loc: CellModel(loc, panel.color_key()) for loc, panel in self.panels.items()}, self._x_stacks(), self._shareable_col_boundaries(options))
        plan = assign_colorbars(model)

        for col in sorted(plan.flush_col_boundaries):
            for left, right in self._col_pairs(col):
                self.panels[left].share_y_axis(self.panels[right])
            self.flush_col_boundaries.add(col)

        for assignment in plan.colorbars:
            keyed = [(self.panels[loc], artist, info) for loc in assignment.keyed for artist, info in self.panels[loc].color_artists]
            # Images keyed together share a color quantity, unless a lone panel mixes several: then one bar each.
            for key in dict.fromkeys(color_key(info) for _, _, info in keyed):
                self._add_colorbar(assignment, [(panel, artist, info) for panel, artist, info in keyed if color_key(info) == key])

    def _add_colorbar(self, assignment: ColorbarAssignment, keyed: list):
        _, first_artist, first_info = keyed[0]
        cbar = self.fig.colorbar(first_artist, cax=self.fig.add_axes((0.0, 0.0, 1.0, 1.0)), orientation=assignment.orientation)  # the layout engine places it
        if minor_locator := first_info.dim_scales[first_info.color_dim].minor_locator():
            cbar.minorlocator = minor_locator
        plt_util.update_shared_cbar([artist for _, artist, _ in keyed], [info.dim_bounds[info.color_dim] for _, _, info in keyed])

        owner = self.panels[assignment.anchors[0]]
        texts = owner.add_colorbar(cbar, assignment, first_info)
        one_line = assignment.orientation == "horizontal"
        infos = [info for _, _, info in keyed]
        if all(info.subject_dim == info.color_dim for info in infos):
            fallback = UnitLabeler(lambda _: None, "color", infos, line_break_before_unit=not one_line)._get_label()
            shared = SharedColorbarLabel(texts.top.set_text, fallback)
            for i, (panel, _, info) in enumerate(keyed):
                panel.wire_colorbar_labeler(info, shared.setter(i), one_line=one_line, fallback_parent=self.suptitle_labeler)
        else:  # e.g. particles colored by a quantity: no subject to name
            owner.cbar_labelers.append(UnitLabeler(texts.top.set_text, "color", infos, line_break_before_unit=not one_line))

    def separate_junction_labels(self, renderer: RendererBase):
        """Where panels sit flush, hide the label of the panel below (or right) nearest the edge if it crowds its
        neighbor's."""
        for panel in self.panels.values():
            if below := panel.shared_x_below:
                for above_ax, below_ax in zip(panel.axes, below.axes):  # main axes, and twins if both have one
                    tick_labels.separate_junction_labels(above_ax.yaxis, below_ax.yaxis, renderer)
            if right := panel.shared_y_right:
                tick_labels.separate_junction_labels(panel.axes[0].xaxis, right.axes[0].xaxis, renderer)

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
