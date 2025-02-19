import pscpy
import xarray

from . import file_util


def load_ds(bp_name: str, step: int) -> xarray.Dataset:
    ds = xarray.load_dataset(file_util.ROOT_DIR / f"{bp_name}.{step:09}.bp")
    ds = pscpy.decode_psc(ds, ["e", "i"])
    return ds


def get_im_data(ds: xarray.Dataset, var: str) -> xarray.DataArray:
    return ds[var].isel(x=0)
