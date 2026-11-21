from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.backend_bases import RendererBase
from matplotlib.cm import ScalarMappable
from matplotlib.colorbar import Colorbar
from matplotlib.colors import to_rgba
from matplotlib.font_manager import FontProperties
from matplotlib.projections import PolarAxes
from matplotlib.text import Text
from matplotlib.transforms import Bbox, ScaledTranslation

from lib.latex import float_to_latex_str
from lib.plotting import plt_util, tick_labels
from lib.plotting.axis_id import AxId, AxIdPolar, AxIdXY
from lib.plotting.bounds_setter import BoundsSetter
from lib.plotting.data_setter import DataSetter
from lib.plotting.labeler import ColorbarLabeler, Labeler, SubjectLabeler, UnitLabeler, YAxisLabeler
from lib.plotting.layout.colorbars import ColorbarAssignment, ColorKey
from lib.plotting.plot_info import PlotInfo, PlotInfo2D, PlotInfoColor, PolarMeshInfo
from lib.plotting.style import LEGEND_TEXT_SCALE, scaled_font_size
from lib.plotting.ticks import InwardTicks
from lib.scale import LinearScale, Scale

type AxAndIdXY = tuple[Axes, AxIdXY]
type AxAndId = tuple[Axes, AxIdXY] | tuple[PolarAxes, AxIdPolar]


COLORBAR_TEXT_PAD = 4.0
"""Points between a colorbar's end and its text."""


def color_key(info: PlotInfoColor) -> ColorKey:
    """What images must agree on to share a colorbar: their color dim's display, unit and scale."""
    return (info.dim_displays[info.color_dim], info.dim_units[info.color_dim], info.dim_scales[info.color_dim])


@dataclass
class ColorbarText:
    """A colorbar's horizontal texts: its label above the bar, and its multiplier/offset below it. They hang off the
    bar's left edge, in fixed units, so the bar can move and resize under them."""

    cbar: Colorbar
    top: Text
    bottom: Text
    multiplier_exponent: int = 0

    @staticmethod
    def create(cbar: Colorbar) -> ColorbarText:
        """On a vertical bar, the label goes above it, from its left edge, and the multiplier below; on a horizontal
        one, the label centered above and the multiplier at its right end."""
        ax = cbar.ax
        fig = ax.get_figure(root=True)
        size = scaled_font_size("axes.labelsize")
        pad = COLORBAR_TEXT_PAD / 72
        x, ha = (0.5, "center") if cbar.orientation == "horizontal" else (0.0, "left")
        top = ax.text(x, 1.0, "", transform=ax.transAxes + ScaledTranslation(0.0, pad, fig.dpi_scale_trans), ha=ha, va="bottom", multialignment=ha, fontsize=size)
        tick_size = FontProperties(size=plt.rcParams["ytick.labelsize"]).get_size_in_points()  # it qualifies the tick labels
        if cbar.orientation == "horizontal":
            bottom = ax.text(1.0, 0.5, "", transform=ax.transAxes + ScaledTranslation(pad, 0.0, fig.dpi_scale_trans), ha="left", va="center", fontsize=tick_size)
        else:
            bottom = ax.text(0.0, 0.0, "", transform=ax.transAxes + ScaledTranslation(0.0, -pad, fig.dpi_scale_trans), ha="left", va="top", fontsize=tick_size)
        return ColorbarText(cbar, top, bottom)

    def update_bottom(self):
        # matplotlib's offset text folds in the multiplier too, so build the offset from the formatter instead.
        self.cbar.long_axis.get_offset_text().set_visible(False)
        offset = getattr(self.cbar.long_axis.get_major_formatter(), "offset", 0.0)

        multiplier = f"$\\times 10^{{{self.multiplier_exponent}}}$" if self.multiplier_exponent else ""
        shift = f"${'+' if offset > 0 else ''}{float_to_latex_str(offset, '.4g')}$" if offset else ""
        self.bottom.set_text(" ".join(part for part in [multiplier, shift] if part))


def _get_colorbar_colors_beneath(cbar: Colorbar) -> Callable[[Bbox], np.ndarray]:
    """What's beneath a point of a colorbar: its colormap at the value there."""

    def colors_beneath(bbox: Bbox) -> np.ndarray:
        x, y = cbar.ax.transData.inverted().transform(((bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2))
        return np.array(cbar.mappable.to_rgba(x if cbar.orientation == "horizontal" else y))[None, :]

    return colors_beneath


@dataclass
class Panel:
    title_labeler: SubjectLabeler | None = field(init=False, default=None)
    legend_labelers_per_axes: dict[Axes, list[SubjectLabeler]] = field(init=False, default_factory=dict)
    cbar_labelers: list[Labeler] = field(init=False, default_factory=list)
    color_artists: list[tuple[ScalarMappable, PlotInfoColor]] = field(init=False, default_factory=list)
    """What needs a colorbar (images, colored scatter), with its info. The grid decides which colorbars it gets."""
    colorbars: list[Colorbar] = field(init=False, default_factory=list)
    """The colorbars this panel owns: it's the first they attach to. They may key other panels' images too."""
    colorbar_assignments: list[ColorbarAssignment] = field(init=False, default_factory=list)
    """Parallel to `colorbars`."""
    colorbar_texts: list[ColorbarText] = field(init=False, default_factory=list)
    data_setters: list[DataSetter] = field(init=False, default_factory=list)
    x_labelers_per_axes: dict[Axes, UnitLabeler] = field(init=False, default_factory=dict)
    y_labelers_per_axes: dict[Axes, YAxisLabeler] = field(init=False, default_factory=dict)
    bounds_setters_per_axis: dict[AxAndIdXY, BoundsSetter] = field(init=False, default_factory=dict)
    scales_per_axis: dict[AxAndId, Scale] = field(init=False, default_factory=dict)
    axes: list[Axes] = field(init=False, default_factory=list)
    """The panel's axes, main first, then any twin."""
    shared_x_below: Panel | None = field(init=False, default=None)
    shared_y_right: Panel | None = field(init=False, default=None)
    inward_ticks: list[InwardTicks] = field(init=False, default_factory=list)

    def update_data(self):
        for data_setter in self.data_setters:
            data_setter.update()

    def update_bounds(self):
        for bounds_setter in self.bounds_setters_per_axis.values():
            bounds_setter.update()

    def update_labels(self):
        self.update_label_texts()
        for axes, labelers in self.legend_labelers_per_axes.items():
            if not any(labeler._get_label() for labeler in labelers):
                if legend := axes.get_legend():
                    legend.remove()
            else:
                axes.legend(fontsize=scaled_font_size("legend.fontsize", LEGEND_TEXT_SCALE))  # required for label redraw

    def update_label_texts(self):
        """Set every label's text for the current frame, but leave the legends be."""
        for labeler in self.get_labelers():
            labeler.update()

    def get_labelers(self) -> list[Labeler]:
        maybe_labelers = [
            self.title_labeler,
            *self.cbar_labelers,
            *(legend_labeler for labelers in self.legend_labelers_per_axes.values() for legend_labeler in labelers),
            *self.x_labelers_per_axes.values(),
            *self.y_labelers_per_axes.values(),
        ]
        return [labeler for labeler in maybe_labelers if labeler]

    def get_subject_labelers(self, *, toplevel_only: bool = False) -> list[SubjectLabeler]:
        subject_labelers = [labeler for labeler in self.get_labelers() if isinstance(labeler, SubjectLabeler)]

        if toplevel_only:
            return [labeler for labeler in subject_labelers if labeler.parent is None]
        return subject_labelers

    def wire_title(self, title: Text):
        """Must come first, so the labelers wired after it can join the title's tree."""
        assert not self.get_labelers()
        title.set_fontsize(scaled_font_size("axes.titlesize"))
        self.title_labeler = SubjectLabeler(title.set_text)

    def add_axes(self, ax: Axes):
        """Add one of the panel's axes, main first."""
        ax.xaxis.label.set_fontsize(scaled_font_size("axes.labelsize"))
        ax.yaxis.label.set_fontsize(scaled_font_size("axes.labelsize"))
        self.axes.append(ax)

    def wire_legend_label(self, artist: Artist, info: PlotInfo):
        legend_labeler = SubjectLabeler(artist.set_label, info)

        axes = artist.axes
        assert axes is not None
        self.legend_labelers_per_axes.setdefault(axes, []).append(legend_labeler)

        # A line whose subject is its y dim is labeled by its y axis first. Anything else goes straight to the title.
        if isinstance(info, PlotInfo2D) and info.subject_dim == info.y_dim:
            self.y_labelers_per_axes[axes].add_child(legend_labeler)
        elif self.title_labeler:
            self.title_labeler.add_child(legend_labeler)

    def color_key(self) -> ColorKey | None:
        """What a colorbar keying this panel's images must show: the display, unit and scale of their color dim.
        `None` if nothing here needs a colorbar; a key of its own if its images can't share one bar."""
        keys = {color_key(info) for _, info in self.color_artists}
        if not keys:
            return None
        if len(keys) > 1:
            return ("unshareable", id(self))
        [key] = keys
        if self.title_labeler is None:
            # Without a title (e.g. stacked), only a colorbar's label can say which coord values each image shows,
            # so it can only be shared with images showing the same ones on every frame.
            frames = {tuple(tuple(sorted((dim, float(value)) for dim, value in values.items())) for values in info.frames_scalar_coord_values) for _, info in self.color_artists}
            key = (key, tuple(sorted(frames)))
        return key

    def add_colorbar(self, cbar: Colorbar, assignment: ColorbarAssignment, info: PlotInfoColor) -> ColorbarText:
        """Own `cbar`, which keys `info` (and maybe others like it)."""
        self.colorbars.append(cbar)
        self.colorbar_assignments.append(assignment)
        texts = ColorbarText.create(cbar)
        self.colorbar_texts.append(texts)

        # Log and symlog scales label their ticks with the exponent already.
        is_linear = isinstance(info.dim_scales[info.color_dim], LinearScale)
        texts.multiplier_exponent = plt_util.move_cbar_multiplier_to_label(cbar) if is_linear else 0
        return texts

    def wire_colorbar_labeler(self, info: PlotInfoColor, set_text: Callable[[str], None], *, one_line: bool, fallback_parent: SubjectLabeler | None):
        """Label `info`'s colorbar (which another panel may own) from this panel's tree, so its sublabels can go to
        this panel's title; without one (e.g. stacked), from `fallback_parent`."""
        labeler = ColorbarLabeler(set_text, info, one_line=one_line)
        if parent := self.title_labeler or fallback_parent:
            parent.add_child(labeler)
        self.cbar_labelers.append(labeler)

    def update_cbar_bottom_texts(self):
        """Move each colorbar's offset (e.g. `+1e3`) below the bar, beside its multiplier. The offset is only known
        once the ticks are drawn, so the layout engine calls this after each of its draws."""
        for texts in self.colorbar_texts:
            texts.update_bottom()

    def wire_data_setter(self, data_setter: DataSetter):
        self.data_setters.append(data_setter)

    def wire_bounds_setter_xy(self, ax: Axes, axis_id: AxIdXY, info: PlotInfo2D):
        if bounds_setter := self.bounds_setters_per_axis.get((ax, axis_id)):
            bounds_setter.infos.append(info)
        else:
            create_setter = {"x": BoundsSetter.create_x_bounds_setter, "y": BoundsSetter.create_y_bounds_setter}[axis_id]
            self.bounds_setters_per_axis[(ax, axis_id)] = create_setter(ax, [info])

    def can_wire_unit_labeler_xy(self, ax: Axes, axis_id: AxIdXY, info: PlotInfo2D) -> bool:
        labeler = {"x": self.x_labelers_per_axes, "y": self.y_labelers_per_axes}[axis_id].get(ax)
        return labeler is None or labeler.is_compatible(info)

    def wire_unit_labeler_xy(self, ax: Axes, axis_id: AxIdXY, info: PlotInfo2D):
        match axis_id:
            case "x":
                if x_labeler := self.x_labelers_per_axes.get(ax):
                    x_labeler.sources.append(info)
                else:
                    self.x_labelers_per_axes[ax] = UnitLabeler(ax.set_xlabel, "x", [info])
            case "y":
                if not (y_labeler := self.y_labelers_per_axes.get(ax)):
                    y_labeler = self.y_labelers_per_axes[ax] = YAxisLabeler(ax.set_ylabel)
                    if self.title_labeler:
                        self.title_labeler.add_child(y_labeler)
                y_labeler.add_source(info)

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
        if axis_id != "r" and (minor_locator := new_scale.minor_locator()):
            (ax.xaxis if axis_id == "x" else ax.yaxis).set_minor_locator(minor_locator)

    def _tick_label_axes(self) -> list[Axis]:
        """Every axis with tick labels to keep tidy: the plot area's (not polar) and the colorbars'."""
        axes = [axis for ax in self.axes if ax.name != "polar" for axis in (ax.xaxis, ax.yaxis)]
        return axes + [cbar.long_axis for cbar in self.colorbars]

    def thin_crowded_ticks(self, renderer: RendererBase):
        for axis in self._tick_label_axes():
            tick_labels.thin_crowded_ticks(axis, renderer)

    def tuck_tick_labels(self, renderer: RendererBase):
        for axis in self._tick_label_axes():
            tick_labels.tuck_tick_labels(axis, renderer)

    def add_inward_ticks(self):
        """Inward ticks on every side of the plot area (polar axes keep their own) and on both long sides of each
        colorbar. Call `update_ticks` once the axes are laid out, and each frame."""
        main = self.axes[0]
        if main.name != "polar":
            twin = self.axes[1] if len(self.axes) > 1 else None
            self.inward_ticks.append(InwardTicks.for_axes(main, self._get_colors_beneath, twin=twin))

        for cbar in self.colorbars:
            sides = ("bottom", "top") if cbar.orientation == "horizontal" else ("left", "right")
            self.inward_ticks.append(InwardTicks.for_axes(cbar.ax, _get_colorbar_colors_beneath(cbar), sides=sides))

    def update_ticks(self):
        for ticks in self.inward_ticks:
            ticks.update()

    def _get_colors_beneath(self, bbox: Bbox) -> np.ndarray:
        """The colors drawn within `bbox` (in display coordinates) on the plot area, as an array of shape `(n, 4)`:
        those of the data where it's known, composited over the background, or else just the background."""
        background = np.array(to_rgba(self.axes[0].get_facecolor()))
        colors = [colors.reshape(-1, 4) for data_setter in self.data_setters if (colors := data_setter.get_colors_within(bbox)) is not None]
        if not colors:
            return background[None, :]

        # Translucent data (e.g. NaNs, which colormaps paint fully transparent) lets the background show through.
        colors = np.concatenate(colors)
        alpha = colors[:, 3:]
        return np.concatenate([alpha * colors[:, :3] + (1 - alpha) * background[:3], np.ones_like(alpha)], axis=1)

    def shares_y_with(self, right: Panel) -> bool:
        return self.shared_y_right is right

    def can_share_y_axis(self, right: Panel) -> bool:
        """Whether this panel's y axis can also serve the panel to its right: one y axis each (no twins), the same
        scale, and a label that reads the same for both. The plot heights must match too; the grid checks those.
        Colorbars are the grid's to arrange around it."""
        if len(self.axes) != 1 or len(right.axes) != 1:
            return False
        my_ax, right_ax = self.axes[0], right.axes[0]
        if (my_ax, "y") not in self.scales_per_axis or (right_ax, "y") not in right.scales_per_axis:
            return False
        if self.scales_per_axis[(my_ax, "y")] != right.scales_per_axis[(right_ax, "y")]:
            return False

        my_labeler = self.y_labelers_per_axes[my_ax].unit_labeler
        right_labeler = right.y_labelers_per_axes[right_ax].unit_labeler
        if not my_labeler.are_compatible(right_labeler.sources):
            return False
        # The shared label must read as each panel's own did, e.g. both B_x, or both just [c].
        merged = UnitLabeler(my_labeler.set_text, "y", my_labeler.sources + right_labeler.sources, require_display_match=False)
        return my_labeler._get_label() == right_labeler._get_label() == merged._get_label()

    def share_y_axis(self, right: Panel):
        """Share this panel's y axis with the panel to its right, which `can_share_y_axis` must allow."""
        my_ax, right_ax = self.axes[0], right.axes[0]
        my_labeler = self.y_labelers_per_axes[my_ax]
        right_labeler = right.y_labelers_per_axes[right_ax]

        right_ax.sharey(my_ax)
        self.shared_y_right = right
        # One axis, so one bounds setter, over both panels' data: two would each set it, the last one winning.
        self.bounds_setters_per_axis[(my_ax, "y")].infos.extend(right.bounds_setters_per_axis.pop((right_ax, "y")).infos)
        right_ax.yaxis.set_tick_params(which="both", labelleft=False)
        right_ax.yaxis.offsetText.set_visible(False)
        for info in right_labeler.unit_labeler.sources:
            my_labeler.add_source(info)
        # The right labeler stays in its tree, still absorbing its legend entries' subjects, but says nothing.
        right_labeler.set_text = right_labeler.unit_labeler.set_text = lambda _: None
        right_ax.set_ylabel("")

    def shares_x_with(self, below: Panel) -> bool:
        return self.shared_x_below is below

    def can_share_x_axis(self, below: Panel) -> bool:
        my_axs = [ax for (ax, id) in self.scales_per_axis if id == "x"]
        below_axs = [ax for (ax, id) in below.scales_per_axis if id == "x"]

        if len(my_axs) != 1 or len(below_axs) != 1:
            return False

        [my_ax] = my_axs
        [below_ax] = below_axs

        if below.scales_per_axis[(below_ax, "x")] != self.scales_per_axis[(my_ax, "x")]:
            return False

        my_labeler = self.x_labelers_per_axes[my_ax]
        below_labeler = below.x_labelers_per_axes[below_ax]
        return below_labeler.are_compatible(my_labeler.sources)

    def share_x_axis(self, below: Panel):
        """Share this panel's x axis with the panel below it, which `can_share_x_axis` must allow."""
        [my_ax] = [ax for (ax, id) in self.scales_per_axis if id == "x"]
        [below_ax] = [ax for (ax, id) in below.scales_per_axis if id == "x"]
        my_labeler = self.x_labelers_per_axes[my_ax]
        below_labeler = below.x_labelers_per_axes[below_ax]

        my_ax.sharex(below_ax)
        self.shared_x_below = below
        # One axis, so one bounds setter, over both panels' data: two would each set it, the last one winning.
        below.bounds_setters_per_axis[(below_ax, "x")].infos.extend(self.bounds_setters_per_axis.pop((my_ax, "x")).infos)
        # Only strip the edge facing `below`. `label_outer` would go by the grid instead, and strip the bottom of
        # every axes above the last row, even one whose neighbour below it didn't share.
        my_ax.xaxis.set_tick_params(which="both", labelbottom=False, bottom=False)
        my_ax.xaxis.offsetText.set_visible(False)
        below_labeler.sources.extend(my_labeler.sources)

        for panel in [self, below]:
            if panel.title_labeler:
                panel.title_labeler.remove_from_tree()
                panel.title_labeler = None

        self.x_labelers_per_axes.pop(my_ax)
        self.scales_per_axis.pop((my_ax, "x"))
