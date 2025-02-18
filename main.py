import pscpy
import xarray
import matplotlib.pyplot as plt
from matplotlib.image import AxesImage


def load_ds(bp_name: str, step: int) -> xarray.Dataset:
    ds = xarray.load_dataset(f"/Users/james/Code/cc/PSC/psc-runs/psc_shock/{bp_name}.{step:09}.bp")
    ds = pscpy.decode_psc(ds, ["e", "i"])
    return ds


bp_name = "pfd_moments"
step = 1000
ds = load_ds(bp_name, step)

var = "rho_e"
im_data = ds[var].isel(x=0)

fig, ax = plt.subplots()

im = ax.imshow(im_data)
cbar = fig.colorbar(im)


def update_cbar(im: AxesImage):
    im_data = im.get_array()
    data_min = im_data.min()
    data_max = im_data.max()

    if data_min >= 0:
        cmin = 0
        cmax = data_max
        cmap = "inferno"
    elif data_max <= 0:
        cmin = data_min
        cmax = 0
        cmap = "inferno_r"
    else:
        cmax = max(abs(im_data.max()), abs(im_data.min()))
        cmin = -cmax
        cmap = "RdBu_r"

    im.set_clim(cmin, cmax)
    im.set_cmap(plt.get_cmap(cmap))


update_cbar(im)

ax.set_title(f"{var} (t={ds.time:.2f})")
ax.set_xlabel("y index")
ax.set_ylabel("z index")

plt.show()
