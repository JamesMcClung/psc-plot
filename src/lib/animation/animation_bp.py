from .. import bp_util, file_util, plt_util
from .animation_base import Animation

__all__ = ["BpAnimation2d"]


class BpAnimation2d(Animation):
    def __init__(self, steps: list[int], prefix: file_util.BpPrefix, variable: str):
        super().__init__(steps)

        self.prefix = prefix
        self.variable = variable

        ds = bp_util.load_ds(self.prefix, self.steps[0])
        im_data = bp_util.get_im_data(ds, self.variable)

        self.im = self.ax.imshow(im_data)

        self.fig.colorbar(self.im)
        plt_util.update_cbar(self.im)

        plt_util.update_title(self.ax, self.variable, ds.time)
        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel("y index")
        self.ax.set_ylabel("z index")

    def _update_fig(self, step: int):
        ds = bp_util.load_ds(self.prefix, step)
        im_data = bp_util.get_im_data(ds, self.variable)

        self.im.set_array(im_data)
        plt_util.update_title(self.ax, self.variable, ds.time)
        plt_util.update_cbar(self.im)
        return [self.im, self.ax.title]
