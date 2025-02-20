import numpy as np

from .. import h5_util
from .animation_base import Animation

__all__ = ["H5Animation"]


class H5Animation(Animation):
    def __init__(self, steps: list[int], h5_name: str):
        self.h5_name = h5_name
        super().__init__(steps)

    def _init_fig(self):
        df = h5_util.load_df(self.h5_name, self.steps[0])

        binned_data, self.x_edges, self.y_edges = np.histogram2d(
            df["y"],
            df["z"],
            bins=[16, 16],
            weights=df["w"],
            density=True,
        )
        binned_data = binned_data.T

        self.mesh = self.ax.pcolormesh(self.x_edges, self.y_edges, binned_data, cmap="inferno")

        self.fig.colorbar(self.mesh)

        self.ax.set_xlabel("y")
        self.ax.set_ylabel("z")
        self.ax.set_title("reduced f")

    def _update_fig(self, step: int):
        df = h5_util.load_df(self.h5_name, step)

        binned_data, _, _ = np.histogram2d(
            df["y"],
            df["z"],
            bins=[self.x_edges, self.y_edges],
            weights=df["w"],
            density=True,
        )
        binned_data = binned_data.T

        self.mesh.set_array(binned_data)

        return [self.mesh]
