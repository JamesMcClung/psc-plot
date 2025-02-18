import pscpy
import xarray
import matplotlib.pyplot as plt

ds = xarray.load_dataset("/Users/james/Code/cc/PSC/psc-runs/psc_shock/pfd_moments.000000000.bp")
ds = pscpy.decode_psc(ds, ["e", "i"])

var = "rho_e"
im_data = ds[var].isel(x=0)

im = plt.imshow(im_data)
cbar = plt.colorbar(im)

plt.title(var)
plt.xlabel("y index, maybe")
plt.ylabel("z index, maybe")

plt.show()
