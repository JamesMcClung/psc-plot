from .. import plt_util
from .. import bp_util
from .animation_base import Animation

__all__ = ["BpAnimation"]


class BpAnimation(Animation):
    def __init__(self, steps: list[int], bp_name: str, var: str):
        self.bp_name = bp_name
        self.var = var
        super().__init__(steps)

    def _init_fig(self):
        ds = bp_util.load_ds(self.bp_name, self.steps[0])
        im_data = bp_util.get_im_data(ds, self.var)

        self.im = self.ax.imshow(im_data)

        self.fig.colorbar(self.im)
        plt_util.update_cbar(self.im)

        plt_util.update_title(self.ax, self.var, ds.time)
        self.ax.set_xlabel("y index")
        self.ax.set_ylabel("z index")

    def _update_fig(self, step: int):
        ds = bp_util.load_ds(self.bp_name, step)
        im_data = bp_util.get_im_data(ds, self.var)

        self.im.set_array(im_data)
        plt_util.update_title(self.ax, self.var, ds.time)
        plt_util.update_cbar(self.im)
        return [self.im, self.ax.title]
