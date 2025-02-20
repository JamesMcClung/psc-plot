import numpy as np

from .. import h5_util
from .. import plt_util
from .animation_base import Animation

__all__ = ["H5Animation"]


class H5Animation(Animation):
    def __init__(self, steps: list[int], h5_name: str, vars: tuple[str, str], nbins: tuple[int, int]):
        self.h5_name = h5_name
        self.vars = vars
        self.nbins = nbins
        super().__init__(steps)

    def _init_fig(self):
        df = h5_util.load_df(self.h5_name, self.steps[0])

        binned_data, self.x_edges, self.y_edges = np.histogram2d(
            df[self.vars[0]],
            df[self.vars[1]],
            bins=self.nbins,
            weights=df["w"],
            density=True,
        )
        binned_data = binned_data.T

        self.mesh = self.ax.pcolormesh(self.x_edges, self.y_edges, binned_data, cmap="inferno")

        self.fig.colorbar(self.mesh)
        plt_util.update_cbar(self.mesh)

        self.ax.set_xlabel(self.vars[0])
        self.ax.set_ylabel(self.vars[1])
        self.ax.set_title("reduced f")

    def _update_fig(self, step: int):
        df = h5_util.load_df(self.h5_name, step)

        binned_data, _, _ = np.histogram2d(
            df[self.vars[0]],
            df[self.vars[1]],
            bins=[self.x_edges, self.y_edges],
            weights=df["w"],
            density=True,
        )
        binned_data = binned_data.T

        self.mesh.set_array(binned_data)
        plt_util.update_cbar(self.mesh)

        return [self.mesh]
