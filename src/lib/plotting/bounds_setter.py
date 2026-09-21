from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from matplotlib.axes import Axes

from lib.plotting.plot_info import PlotInfo, PlotInfo2D

type Bound = float | None
type Bounds = tuple[Bound, Bound]


@dataclass
class BoundsSetter[I: PlotInfo = PlotInfo]:
    set_bounds: Callable[[Bound, Bound], None]
    get_bounds: Callable[[I], Bounds]
    infos: list[I]

    _prev_bounds: Bounds = field(default=(None, None), init=False)

    def _find_widest_bounds(self) -> Bounds:
        lowest_bound = None
        highest_bound = None

        for info in self.infos:
            bounds = self.get_bounds(info)

            if lowest_bound is None:
                lowest_bound = bounds[0]
            elif bounds[0] is not None and lowest_bound > bounds[0]:
                lowest_bound = bounds[0]

            if highest_bound is None:
                highest_bound = bounds[1]
            elif bounds[1] is not None and highest_bound < bounds[1]:
                highest_bound = bounds[1]

        return (lowest_bound, highest_bound)

    def update(self):
        bounds = self._find_widest_bounds()
        if bounds == self._prev_bounds:
            return

        self.set_bounds(self._find_widest_bounds())
        self._prev_bounds = bounds

    @staticmethod
    def create_x_bounds_setter[I: PlotInfo2D](ax: Axes, infos: list[I]) -> BoundsSetter[I]:
        return BoundsSetter(ax.set_xlim, lambda info: info.dim_bounds[info.x_dim], infos)

    @staticmethod
    def create_y_bounds_setter[I: PlotInfo2D](ax: Axes, infos: list[I]) -> BoundsSetter[I]:
        return BoundsSetter(ax.set_ylim, lambda info: info.dim_bounds[info.y_dim], infos)
