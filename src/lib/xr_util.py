import pscpy
import xarray

from . import file_util


def load_ds(bp_name: str, step: int) -> xarray.Dataset:
    ds = xarray.load_dataset(file_util.get_data_path(bp_name, step, "bp"))
    ds = pscpy.decode_psc(ds, ["e", "i"])
    return ds


def get_im_data(ds: xarray.Dataset, var: str) -> xarray.DataArray:
    return ds[var].isel(x=0)
