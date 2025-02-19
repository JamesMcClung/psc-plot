import pscpy
import xarray

from . import file_util


def get_available_steps_bp(bp_name: str) -> list[int]:
    return file_util.get_available_steps(f"{bp_name}.", ".bp")


def load_ds(bp_name: str, step: int) -> xarray.Dataset:
    data_path = file_util.ROOT_DIR / f"{bp_name}.{step:09}.bp"
    ds = xarray.load_dataset(data_path)
    ds = pscpy.decode_psc(ds, ["e", "i"])
    return ds


def get_im_data(ds: xarray.Dataset, var: str) -> xarray.DataArray:
    return ds[var].isel(x=0)
