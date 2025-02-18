import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from lib import plt_util, xr_util


bp_name = "pfd_moments"
steps = xr_util.get_available_steps(bp_name)
step = steps[0]
ds = xr_util.load_ds(bp_name, step)

var = "rho_e"
im_data = xr_util.get_im_data(ds, var)

fig, ax = plt.subplots()

im = ax.imshow(im_data)
cbar = fig.colorbar(im)

plt_util.update_cbar(im)

plt_util.update_title(ax, var, ds.time)
ax.set_xlabel("y index")
ax.set_ylabel("z index")


def update_anim(step: int):
    ds = xr_util.load_ds(bp_name, step)
    im_data = xr_util.get_im_data(ds, var)

    im.set_array(im_data)
    plt_util.update_title(ax, var, ds.time)
    plt_util.update_cbar(im)
    return [im, ax.title]


anim = FuncAnimation(fig, update_anim, frames=steps, blit=False)  # FIXME get blitting to work with the title

plt.show()
