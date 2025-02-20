import pandas

from . import file_util


def get_available_steps_h5(h5_name: str) -> list[int]:
    return file_util.get_available_steps(f"{h5_name}.", "_p000000.h5")


def load_df(h5_name: str, step: int) -> pandas.DataFrame:
    data_path = file_util.ROOT_DIR / f"{h5_name}.{step:06}_p000000.h5"
    df = pandas.read_hdf(data_path)
    return df
