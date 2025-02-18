import pscpy
import xarray
import matplotlib.pyplot as plt
from lib import plt_util


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

plt_util.update_cbar(im)

ax.set_title(f"{var} (t={ds.time:.2f})")
ax.set_xlabel("y index")
ax.set_ylabel("z index")

plt.show()
