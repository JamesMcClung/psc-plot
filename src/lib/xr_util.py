import pathlib

import pscpy
import xarray

ROOT_DIR = pathlib.Path("/Users/james/Code/cc/PSC/psc-runs/psc_shock")


def load_ds(bp_name: str, step: int) -> xarray.Dataset:
    ds = xarray.load_dataset(ROOT_DIR / f"{bp_name}.{step:09}.bp")
    ds = pscpy.decode_psc(ds, ["e", "i"])
    return ds


def get_im_data(ds: xarray.Dataset, var: str) -> xarray.DataArray:
    return ds[var].isel(x=0)
