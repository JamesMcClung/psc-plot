import matplotlib.pyplot as plt

from lib import plt_util, xr_util


bp_name = "pfd_moments"
step = 1000
ds = xr_util.load_ds(bp_name, step)

var = "rho_e"
im_data = xr_util.get_im_data(ds, var)

fig, ax = plt.subplots()

im = ax.imshow(im_data)
cbar = fig.colorbar(im)

plt_util.update_cbar(im)

ax.set_title(f"{var} (t={ds.time:.2f})")
ax.set_xlabel("y index")
ax.set_ylabel("z index")

plt.show()
