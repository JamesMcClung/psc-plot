import pscpy
import xarray


def load_ds(bp_name: str, step: int) -> xarray.Dataset:
    ds = xarray.load_dataset(f"/Users/james/Code/cc/PSC/psc-runs/psc_shock/{bp_name}.{step:09}.bp")
    ds = pscpy.decode_psc(ds, ["e", "i"])
    return ds


def get_im_data(ds: xarray.Dataset, var: str) -> xarray.DataArray:
    return ds[var].isel(x=0)
