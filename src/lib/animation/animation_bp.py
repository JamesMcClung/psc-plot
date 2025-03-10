from .. import plt_util
from .. import bp_util, file_util
from .animation_base import Animation

__all__ = ["BpAnimation"]


class BpAnimation(Animation):
    def __init__(self, steps: list[int], prefix: file_util.BpPrefix, variable: str):
        self.prefix = prefix
        self.variable = variable
        super().__init__(steps)

    def _init_fig(self):
        ds = bp_util.load_ds(self.prefix, self.steps[0])
        im_data = bp_util.get_im_data(ds, self.variable)

        self.im = self.ax.imshow(im_data)

        self.fig.colorbar(self.im)
        plt_util.update_cbar(self.im)

        plt_util.update_title(self.ax, self.variable, ds.time)
        self.ax.set_xlabel("y index")
        self.ax.set_ylabel("z index")

    def _update_fig(self, step: int):
        ds = bp_util.load_ds(self.prefix, step)
        im_data = bp_util.get_im_data(ds, self.variable)

        self.im.set_array(im_data)
        plt_util.update_title(self.ax, self.variable, ds.time)
        plt_util.update_cbar(self.im)
        return [self.im, self.ax.title]
