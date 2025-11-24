import dask.dataframe as dd

from .. import file_util, particle_util
from ..derived_particle_variables import derive_particle_variable
from .keys import VAR_LATEX_KEY
from .source import DataSource


class ParticleLoader(DataSource):
    def __init__(self, prefix: file_util.ParticlePrefix, var_names: list[str]):
        self.prefix = prefix
        self.var_names = var_names

    def get_data(self, steps: list[int]) -> dd.DataFrame:
        df = particle_util.load_df(self.prefix, steps)
        for var_name in self.var_names:
            derive_particle_variable(df, var_name, self.prefix)

        df.attrs[VAR_LATEX_KEY] = "f"

        return df

    def get_file_prefix(self) -> str:
        return self.prefix

    def get_var_name(self) -> str:
        return "f"

    def get_name_fragments(self) -> list[str]:
        return [self.prefix] + self.var_names
