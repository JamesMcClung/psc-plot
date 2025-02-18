import pscpy
import xarray
import matplotlib.pyplot as plt

ds = xarray.load_dataset("/Users/james/Code/cc/PSC/psc-runs/psc_shock/pfd_moments.000000000.bp")
ds = pscpy.decode_psc(ds, ["e", "i"])

var = "rho_e"
im_data = ds[var].isel(x=0)

im = plt.imshow(im_data)
cbar = plt.colorbar(im)


def set_clim():
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

    plt.clim(cmin, cmax)
    plt.set_cmap(cmap)


set_clim()

plt.title(var)
plt.xlabel("y index, maybe")
plt.ylabel("z index, maybe")

plt.show()
