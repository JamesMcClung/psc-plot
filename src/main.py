import matplotlib.pyplot as plt

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

plt.show()
