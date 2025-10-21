import typing

import numpy as np
import pscpy
import xarray

from . import file_util

type BpDim = typing.Literal["x", "y", "z"]
BP_DIMS: list[BpDim] = list(BpDim.__value__.__args__)

DEFAULT_TIME_UNIT_LATEX = "$\\omega_\\text{pe}^{-1}$"
DEFAULT_SPACE_UNIT_LATEX = "$d_\\text{e}$"


def get_available_steps_bp(prefix: file_util.BpPrefix) -> list[int]:
    return file_util.get_available_steps(f"{prefix}.", ".bp")


def load_ds(prefix: file_util.BpPrefix, step: int) -> xarray.Dataset:
    data_path = file_util.ROOT_DIR / f"{prefix}.{step:09}.bp"
    ds = xarray.load_dataset(data_path)
    # FIXME don't hardcode species names
    ds = pscpy.decode_psc(ds, ["e", "i"])
    return ds
