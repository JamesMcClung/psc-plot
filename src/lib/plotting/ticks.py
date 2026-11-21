"""Ticks that point inward on every side of an axes, each colored to stand out against what's beneath it.

They're scatter artists of their own, not the axes' ticks: matplotlib points all of an edge's ticks one way and
gives them one color. The axes' own ticks are hidden (zero length); their labels stay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.collections import PathCollection
from matplotlib.markers import TICKDOWN, TICKLEFT, TICKRIGHT, TICKUP
from matplotlib.transforms import Bbox, Transform

from lib.plotting import plt_util

type Side = Literal["left", "right", "bottom", "top"]
type ColorsBeneath = Callable[[Bbox], np.ndarray]
"""The RGBA colors, of shape `(n, 4)`, drawn within a bbox in display coordinates."""

SIDES: tuple[Side, ...] = ("left", "right", "bottom", "top")
_MARKERS = {"bottom": TICKUP, "top": TICKDOWN, "left": TICKRIGHT, "right": TICKLEFT}


def hide_axis_ticks(ax: Axes):
    """Zero the length of the axes' own ticks, keeping their labels where inward ticks would leave them."""
    for axis_id in ("x", "y"):
        pad = plt.rcParams[f"{axis_id}tick.major.pad"]
        ax.tick_params(axis=axis_id, which="both", length=0, pad=pad)


@dataclass
class InwardTicks:
    ax: Axes
    """Whose spines the ticks sit on."""
    axes_for_side: dict[Side, Axes]
    """Whose axis gives each side's tick locations (e.g. a twin's y axis for the right side)."""
    colors_beneath: ColorsBeneath
    artists: dict[tuple[Side, bool], PathCollection] = field(default_factory=dict)
    """Keyed by side and whether minor."""

    @staticmethod
    def for_axes(ax: Axes, colors_beneath: ColorsBeneath, *, sides: tuple[Side, ...] = SIDES, twin: Axes | None = None) -> InwardTicks:
        axes_for_side: dict[Side, Axes] = {side: (twin if side == "right" and twin else ax) for side in sides}
        ticks = InwardTicks(ax, axes_for_side, colors_beneath)

        for side_ax in {*axes_for_side.values()}:
            hide_axis_ticks(side_ax)

        for side in sides:
            for minor in (False, True):
                rc = f"{'x' if side in ('bottom', 'top') else 'y'}tick.{'minor' if minor else 'major'}"
                artist = ax.scatter([], [], s=plt.rcParams[f"{rc}.size"] ** 2, marker=_MARKERS[side], facecolors="none", linewidths=plt.rcParams[f"{rc}.width"], clip_on=False, zorder=2.5)
                artist.set_in_layout(False)
                ticks.artists[(side, minor)] = artist

        return ticks

    def _axis(self, side: Side) -> Axis:
        side_ax = self.axes_for_side[side]
        return side_ax.xaxis if side in ("bottom", "top") else side_ax.yaxis

    def _transform(self, side: Side) -> Transform:
        side_ax = self.axes_for_side[side]
        return side_ax.get_xaxis_transform() if side in ("bottom", "top") else side_ax.get_yaxis_transform()

    def update(self):
        """Place every tick at its axis' tick locations, colored against what's beneath it."""
        for (side, minor), artist in self.artists.items():
            axis = self._axis(side)
            lower, upper = sorted(axis.get_view_interval())
            locs = [loc for loc in (axis.get_minorticklocs() if minor else axis.get_majorticklocs()) if lower <= loc <= upper]

            edge = 1.0 if side in ("top", "right") else 0.0
            offsets = np.array([(loc, edge) if side in ("bottom", "top") else (edge, loc) for loc in locs]).reshape(-1, 2)
            artist.set_offsets(offsets)
            artist.set_offset_transform(self._transform(side))  # the offsets; the markers stay in points

            size_key = f"{'x' if side in ('bottom', 'top') else 'y'}tick.{'minor' if minor else 'major'}.size"
            length = plt.rcParams[size_key] * self.ax.get_figure(root=True).dpi / 72
            artist.set_edgecolor([plt_util.get_opposite_color(self.colors_beneath(self._tick_bbox(side, offset, length))) for offset in offsets])

    def _tick_bbox(self, side: Side, offset: np.ndarray, length: float) -> Bbox:
        """The strip of display a tick covers, running inward from its edge."""
        x, y = self._transform(side).transform(offset)
        match side:
            case "bottom":
                return Bbox.from_extents(x - 0.5, y, x + 0.5, y + length)
            case "top":
                return Bbox.from_extents(x - 0.5, y - length, x + 0.5, y)
            case "left":
                return Bbox.from_extents(x, y - 0.5, x + length, y + 0.5)
            case "right":
                return Bbox.from_extents(x - length, y - 0.5, x, y + 0.5)
