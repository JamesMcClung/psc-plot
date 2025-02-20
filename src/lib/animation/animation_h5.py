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

        binned_data, y_edges, z_edges = np.histogram2d(
            df["y"],
            df["z"],
            bins=[60, 80],
            weights=df["w"],
        )
        binned_data = binned_data.T

        self.mesh = self.ax.pcolormesh(y_edges, z_edges, binned_data, cmap="inferno")

        self.fig.colorbar(self.mesh)

        self.ax.set_xlabel("y")
        self.ax.set_ylabel("z")
        self.ax.set_title("reduced f")

    def _update_fig(self, step: int):
        df = h5_util.load_df(self.h5_name, step)

        coords = self.mesh.get_coordinates()  # array of dimension (nrows, ncols, 2), where nrows/ncols refers to mesh vertices and 2 is x/y
        bins = [coords[0, :, 0], coords[:, 0, 1]]

        binned_data, _, _ = np.histogram2d(
            df["y"],
            df["z"],
            bins=bins,
            weights=df["w"],
        )
        binned_data = binned_data.T

        self.mesh.set_array(binned_data)

        return [self.mesh]
