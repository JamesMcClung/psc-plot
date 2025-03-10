import pscpy
import xarray

from . import file_util


def get_available_steps_bp(prefix: file_util.BpPrefix) -> list[int]:
    return file_util.get_available_steps(f"{prefix}.", ".bp")


def load_ds(prefix: file_util.BpPrefix, step: int) -> xarray.Dataset:
    data_path = file_util.ROOT_DIR / f"{prefix}.{step:09}.bp"
    ds = xarray.load_dataset(data_path)
    ds = pscpy.decode_psc(ds, ["e", "i"])
    return ds


def get_im_data(ds: xarray.Dataset, variable: str) -> xarray.DataArray:
    return ds[variable].isel(x=0)
