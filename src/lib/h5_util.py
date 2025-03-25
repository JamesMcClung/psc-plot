import typing

import pandas

from . import file_util

type PrtVariable = typing.Literal["x", "y", "z", "px", "py", "pz", "q", "m", "w", "id", "tag"]
PRT_VARIABLES: list[PrtVariable] = list(PrtVariable.__value__.__args__)


def get_available_steps_h5(prefix: file_util.H5Prefix) -> list[int]:
    return file_util.get_available_steps(f"{prefix}.", "_p000000.h5")


def load_df(prefix: file_util.H5Prefix, step: int) -> pandas.DataFrame:
    data_path = file_util.ROOT_DIR / f"{prefix}.{step:06}_p000000.h5"
    df = pandas.read_hdf(data_path, key="particles/p0/1d")
    return df
