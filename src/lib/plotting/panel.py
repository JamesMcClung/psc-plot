from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.collections import PathCollection
from matplotlib.colorbar import Colorbar
from matplotlib.colors import to_rgba
from matplotlib.markers import TICKDOWN, TICKUP
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
from matplotlib.projections import PolarAxes
from matplotlib.text import Text
from matplotlib.ticker import MaxNLocator
from matplotlib.transforms import Bbox

from lib.plotting import plt_util
from lib.plotting.axis_id import AxId, AxIdPolar, AxIdXY
from lib.plotting.bounds_setter import BoundsSetter
from lib.plotting.data_setter import DataSetter
from lib.plotting.labeler import Labeler, SubjectAndUnitLabeler, SubjectLabeler, UnitLabeler
from lib.plotting.plot_info import PlotInfo, PlotInfo2D, PlotInfoColor, PolarMeshInfo
from lib.scale import LinearScale, Scale

type AxAndIdXY = tuple[Axes, AxIdXY]
type AxAndId = tuple[Axes, AxIdXY] | tuple[PolarAxes, AxIdPolar]
type YEnd = Literal["lower", "upper"]


@dataclass
class Panel:
    title_labeler: SubjectLabeler | None = field(init=False, default=None)
    legend_labelers_per_axes: dict[Axes, list[SubjectLabeler]] = field(init=False, default_factory=dict)
    cbar_labeler: Labeler | None = field(init=False, default=None)
    colorbars: list[Colorbar] = field(init=False, default_factory=list)
    data_setters: list[DataSetter] = field(init=False, default_factory=list)
    unit_labelers_per_axis: dict[AxAndIdXY, UnitLabeler] = field(init=False, default_factory=dict)
    bounds_setters_per_axis: dict[AxAndIdXY, BoundsSetter] = field(init=False, default_factory=dict)
    scales_per_axis: dict[AxAndId, Scale] = field(init=False, default_factory=dict)
    flush_y_ends: set[YEnd] = field(init=False, default_factory=set)
    """Ends at which this panel touches its vertical neighbour, so nothing may stick out past them."""
    interior_x_ticks: dict[tuple[Axes, YEnd], PathCollection] = field(init=False, default_factory=dict)
    """Ticks drawn just inside the axes at an end, over the data, in addition to any axis ticks there."""

    def update_data(self):
        for data_setter in self.data_setters:
            data_setter.update()

    def update_bounds(self):
        for bounds_setter in self.bounds_setters_per_axis.values():
            bounds_setter.update()

    def update_labels(self):
        for labeler in self.get_labelers():
            labeler.update()

        for axes, labelers in self.legend_labelers_per_axes.items():
            if not any(labeler._get_label() for labeler in labelers):
                if legend := axes.get_legend():
                    legend.remove()
            else:
                axes.legend()  # required for label redraw

    def get_labelers(self) -> list[Labeler]:
        maybe_labelers = [
            self.title_labeler,
            self.cbar_labeler,
            *(legend_labeler for labelers in self.legend_labelers_per_axes.values() for legend_labeler in labelers),
            *(unit_labeler for unit_labeler in self.unit_labelers_per_axis.values()),
        ]
        return [labeler for labeler in maybe_labelers if labeler]

    def get_subject_labelers(self, *, toplevel_only: bool = False) -> list[SubjectLabeler]:
        subject_labelers: list[SubjectLabeler] = []

        for labeler in self.get_labelers():
            if isinstance(labeler, SubjectLabeler):
                subject_labelers.append(labeler)
            elif isinstance(labeler, SubjectAndUnitLabeler):
                subject_labelers.append(labeler.subject_labeler)

        if toplevel_only:
            return [labeler for labeler in subject_labelers if labeler.parent is None]
        return subject_labelers

    def wire_title(self, title: Text, info: PlotInfo | None = None):
        self.title_labeler = SubjectLabeler(title.set_text, info)
        for legend_labelers in self.legend_labelers_per_axes.values():
            for legend_labeler in legend_labelers:
                self.title_labeler.add_child(legend_labeler)
        if self.cbar_labeler and isinstance(self.cbar_labeler, SubjectAndUnitLabeler):
            self.title_labeler.add_child(self.cbar_labeler.subject_labeler)

    def wire_legend_label(self, artist: Artist, info: PlotInfo):
        legend_labeler = SubjectLabeler(artist.set_label, info)

        axes = artist.axes
        assert axes is not None
        self.legend_labelers_per_axes.setdefault(axes, []).append(legend_labeler)

        if self.title_labeler:
            self.title_labeler.add_child(legend_labeler)

    def wire_cbar_label(self, cbar: Colorbar, info: PlotInfoColor):
        self.colorbars.append(cbar)

        # Log and symlog scales label their ticks with the exponent already.
        is_linear = isinstance(info.dim_scales[info.color_dim], LinearScale)
        multiplier_exponent = plt_util.move_cbar_multiplier_to_label(cbar) if is_linear else 0

        # The multiplier gets the first line, which (the label reading bottom to top) is nearest the tick labels.
        multiplier = f"$\\times 10^{{{multiplier_exponent}}}$" if multiplier_exponent else ""

        def set_label(text: str):
            cbar.set_label("\n".join(line for line in [multiplier, text] if line))

        is_subject = info.dim_displays[info.color_dim].maybe_with_dollars() == info.subject
        if is_subject:
            self.cbar_labeler = SubjectAndUnitLabeler(set_label, "color", info)
            if self.title_labeler:
                self.title_labeler.add_child(self.cbar_labeler.subject_labeler)
        else:
            self.cbar_labeler = UnitLabeler(set_label, "color", [info])

    def wire_data_setter(self, data_setter: DataSetter):
        self.data_setters.append(data_setter)

    def wire_bounds_setter_xy(self, ax: Axes, axis_id: AxIdXY, info: PlotInfo2D):
        if bounds_setter := self.bounds_setters_per_axis.get((ax, axis_id)):
            bounds_setter.infos.append(info)
        else:
            create_setter = {"x": BoundsSetter.create_x_bounds_setter, "y": BoundsSetter.create_y_bounds_setter}[axis_id]
            self.bounds_setters_per_axis[(ax, axis_id)] = create_setter(ax, [info])

    def can_wire_unit_labeler_xy(self, ax: Axes, axis_id: AxIdXY, info: PlotInfo2D) -> bool:
        unit_labeler = self.unit_labelers_per_axis.get((ax, axis_id))
        return unit_labeler is None or unit_labeler.is_compatible(info)

    def wire_unit_labeler_xy(self, ax: Axes, axis_id: AxIdXY, info: PlotInfo2D):
        if unit_labeler := self.unit_labelers_per_axis.get((ax, axis_id)):
            unit_labeler.sources.append(info)
        else:
            set_label = {"x": ax.set_xlabel, "y": ax.set_ylabel}[axis_id]
            self.unit_labelers_per_axis[(ax, axis_id)] = UnitLabeler(set_label, axis_id, [info], require_display_match=axis_id == "x")

    def can_wire_scale(self, ax: Axes | PolarAxes, axis_id: AxId, info: PlotInfo2D | PolarMeshInfo) -> bool:
        match axis_id:
            case "x":
                new_scale = info.dim_scales[info.x_dim]
            case "y":
                new_scale = info.dim_scales[info.y_dim]
            case "r":
                new_scale = info.dim_scales[info.r_dim]

        scale = self.scales_per_axis.get((ax, axis_id))
        return scale is None or scale == new_scale

    def wire_scale(self, ax: Axes | PolarAxes, axis_id: AxId, info: PlotInfo2D | PolarMeshInfo):
        if not self.can_wire_scale(ax, axis_id, info):
            raise Exception(f"the {axis_id}-scale of {info} is incompatible with at least one other plot")

        match axis_id:
            case "x":
                new_scale = info.dim_scales[info.x_dim]
                set_scale = ax.set_xscale
            case "y":
                new_scale = info.dim_scales[info.y_dim]
                set_scale = ax.set_yscale
            case "r":
                new_scale = info.dim_scales[info.r_dim]
                set_scale = ax.set_rscale

        self.scales_per_axis[(ax, axis_id)] = new_scale
        set_scale(new_scale.to_axis_scale())

    def prune_y_ticks(self, end: YEnd):
        """Drop the y tick (and its label) at `end`, e.g. so it doesn't crowd the neighbouring axes' own tick
        label there. Locators that can't prune (log, say) are left alone.
        """
        for ax, axis_id in self.scales_per_axis:
            if axis_id != "y":
                continue
            locator = ax.yaxis.get_major_locator()
            if isinstance(locator, MaxNLocator):
                locator.set_params(prune=end)

    def pad_y_end(self, end: YEnd, pad: float):
        """Have constrained layout leave `pad` points of room beyond whatever sits outermost at `end` -- the x
        label at the lower end, the title at the upper -- e.g. to make up for padding it was told not to leave.

        The room is an invisible spacer anchored to that text, since padding the text itself (`labelpad`, the
        title's `pad`) only moves it away from its own axes, not away from the neighbour's.
        """
        # Sharing an axis takes it out of `scales_per_axis`, but not out of `bounds_setters_per_axis`.
        for ax, axis_id in self.bounds_setters_per_axis:
            if axis_id != "x":
                continue
            text, xy, box_alignment = {"lower": (ax.xaxis.label, (0.5, 0.0), (0.5, 1.0)), "upper": (ax.title, (0.5, 1.0), (0.5, 0.0))}[end]
            spacer = AnnotationBbox(DrawingArea(0.0, pad), xy, xycoords=text, box_alignment=box_alignment, frameon=False, pad=0.0, annotation_clip=False)
            ax.add_artist(spacer)

    def add_interior_x_ticks(self):
        """Draw x ticks just inside the top and bottom of the axes, over the data, so that every panel in a stack
        gets its own without any of them taking up room between the axes.

        These are artists of their own rather than the axis' ticks, which at any one end all point the same
        way (so can't add to ticks already pointing out) and all share one color. `update_interior_x_ticks`
        places and colors them, every frame.
        """
        size = plt.rcParams["xtick.major.size"]
        width = plt.rcParams["xtick.major.width"]

        # Sharing an axis takes it out of `scales_per_axis`, but not out of `bounds_setters_per_axis`.
        for ax, axis_id in self.bounds_setters_per_axis:
            if axis_id != "x":
                continue

            for end, marker in [("lower", TICKUP), ("upper", TICKDOWN)]:
                ticks = ax.scatter([], [], s=size**2, marker=marker, facecolors="none", linewidths=width, transform=ax.get_xaxis_transform(), clip_on=False, zorder=2.5)
                ticks.set_in_layout(False)
                self.interior_x_ticks[(ax, end)] = ticks

    def update_interior_x_ticks(self):
        """Put an interior tick at each of the axis' major tick locations, colored to stand out against whatever
        is drawn beneath it."""
        for (ax, end), ticks in self.interior_x_ticks.items():
            lower, upper = sorted(ax.get_xlim())
            xs = [x for x in ax.xaxis.get_majorticklocs() if lower <= x <= upper]
            y, inward = {"lower": (0.0, 1.0), "upper": (1.0, -1.0)}[end]
            ticks.set_offsets(np.array([(x, y) for x in xs]).reshape(-1, 2))

            # What's beneath a tick is the strip of display it covers, running inward from the edge.
            length = plt.rcParams["xtick.major.size"] * ax.get_figure(root=True).dpi / 72
            colors = []
            for x in xs:
                tick_x, edge_y = ax.get_xaxis_transform().transform((x, y))
                y0, y1 = sorted([edge_y, edge_y + inward * length])
                bbox = Bbox.from_extents(tick_x - 0.5, y0, tick_x + 0.5, y1)
                colors.append(plt_util.get_opposite_color(self._get_colors_beneath(ax, bbox)))

            ticks.set_edgecolor(colors)

    def _get_colors_beneath(self, ax: Axes, bbox: Bbox) -> np.ndarray:
        """The colors drawn within `bbox` (in display coordinates) on `ax`, as an array of shape `(n, 4)`: those
        of the data where it's known, composited over the axes' own background, or else just the background."""
        background = np.array(to_rgba(ax.get_facecolor()))
        data_setters = [data_setter for data_setter in self.data_setters if data_setter.artist.axes is ax]
        colors = [colors.reshape(-1, 4) for data_setter in data_setters if (colors := data_setter.get_colors_within(bbox)) is not None]
        if not colors:
            return background[None, :]

        # Translucent data (e.g. NaNs, which colormaps paint fully transparent) lets the background show through.
        colors = np.concatenate(colors)
        alpha = colors[:, 3:]
        return np.concatenate([alpha * colors[:, :3] + (1 - alpha) * background[:3], np.ones_like(alpha)], axis=1)

    def tuck_y_tick_labels(self, renderer: RendererBase):
        """Anchor every y tick label that overhangs a flush end to that end.

        Same rule as `prune_y_ticks`: nothing may stick out past an edge that has to sit flush, or
        constrained layout reserves room for it and the gap comes back. Pruning alone doesn't get there,
        because the tick it leaves behind can still sit within half a label of the edge.

        Every label is put back to its default alignment first, both so that the measurement doesn't
        depend on an earlier tuck and so that ticks that have since moved away from the edge are let go.
        """
        if not self.flush_y_ends:
            return

        axs = [ax for ax, axis_id in self.scales_per_axis if axis_id == "y"]
        default_va = plt.rcParams["ytick.alignment"]  # what matplotlib itself aligns y tick labels by

        for ax in axs:
            box = ax.get_window_extent(renderer)
            for label in ax.get_yticklabels():
                if not label.get_visible():
                    continue

                label.set_va(default_va)
                bbox = label.get_window_extent(renderer)

                if "upper" in self.flush_y_ends and bbox.y0 < box.y1 < bbox.y1:
                    label.set_va("top")
                elif "lower" in self.flush_y_ends and bbox.y0 < box.y0 < bbox.y1:
                    label.set_va("bottom")

    def try_share_x_axis(self, below: Panel) -> bool:
        my_axs = [ax for (ax, id) in self.scales_per_axis if id == "x"]
        below_axs = [ax for (ax, id) in below.scales_per_axis if id == "x"]

        if len(my_axs) != 1 or len(below_axs) != 1:
            return False

        [my_ax] = my_axs
        [below_ax] = below_axs

        if below.scales_per_axis[(below_ax, "x")] != self.scales_per_axis[(my_ax, "x")]:
            return False

        my_labeler = self.unit_labelers_per_axis[(my_ax, "x")]
        below_labeler = below.unit_labelers_per_axis[(below_ax, "x")]
        if not below_labeler.are_compatible(my_labeler.sources):
            return False

        my_ax.sharex(below_ax)
        # Only strip the edge facing `below`. `label_outer` would go by the grid instead, and strip the bottom of
        # every axes above the last row, even one whose neighbour below it didn't share.
        my_ax.xaxis.set_tick_params(which="both", labelbottom=False, bottom=False)
        my_ax.xaxis.offsetText.set_visible(False)
        below_labeler.sources.extend(my_labeler.sources)

        for panel in [self, below]:
            if panel.title_labeler:
                panel.title_labeler.remove_from_tree()
                panel.title_labeler = None

        self.unit_labelers_per_axis.pop((my_ax, "x"))
        self.scales_per_axis.pop((my_ax, "x"))

        return True
