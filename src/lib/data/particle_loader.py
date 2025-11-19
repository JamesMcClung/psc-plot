import pandas as pd
import xarray as xr

from .. import file_util, particle_util
from ..derived_particle_variables import derive_particle_variable
from .pipeline import Pipeline
from .source import DataSource


def _load_particle_df(prefix: file_util.ParticlePrefix, step: int, var_names: list[str]) -> pd.DataFrame:
    df = particle_util.load_df(prefix, step)
    for var_name in var_names:
        derive_particle_variable(df, var_name, prefix)
    return df


def _check_pipeline_to_da(pipeline_to_da: Pipeline):
    pipeline_input = pipeline_to_da.get_input_data_type()
    if not issubclass(pd.DataFrame, pipeline_input):
        raise ValueError(f"pipeline must be able to accept {pd.DataFrame.__name__}, but it only accepts {pipeline_input.__name__}")

    pipeline_output = pipeline_to_da.get_output_data_type()
    if not issubclass(pipeline_output, xr.DataArray):
        raise ValueError(f"pipeline must emit {xr.DataArray.__name__}, not {pipeline_output.__name__}")


class ParticleLoader(DataSource):
    def __init__(self, prefix: file_util.ParticlePrefix, var_names: list[str], pipeline_to_da: Pipeline):
        _check_pipeline_to_da(pipeline_to_da)

        self.prefix = prefix
        self.var_names = var_names
        self.pipeline_to_da = pipeline_to_da

    def get_data_at_step(self, step: int) -> xr.DataArray:
        df = _load_particle_df(self.prefix, step, self.var_names)
        da = self.pipeline_to_da.apply(df)
        return da

    def get_data(self, steps: list[int]) -> xr.DataArray:
        return xr.concat((self.get_data_at_step(step) for step in steps), "t")

    def get_file_prefix(self) -> str:
        return self.prefix

    def get_var_name(self) -> str:
        return "f"

    def get_modified_var_name(self) -> str:
        return "f"

    def get_name_fragments(self) -> list[str]:
        return [self.prefix] + self.var_names
