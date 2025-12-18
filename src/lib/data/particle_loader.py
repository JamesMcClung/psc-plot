from lib.data.data_with_attrs import LazyList

from .. import file_util, particle_util
from ..derived_particle_variables import derive_particle_variable
from .source import DataSource


class ParticleLoader(DataSource):
    def __init__(self, prefix: file_util.ParticlePrefix, var_names: list[str], steps: list[int]):
        self.prefix = prefix
        self.var_names = var_names
        self.steps = steps

    def get_data(self) -> LazyList:
        df = particle_util.load_df(self.prefix, self.steps)

        for var_name in self.var_names:
            df = derive_particle_variable(df, var_name, self.prefix)

        return df.assign_metadata(
            name_fragments=self.get_name_fragments(),
            var_name=self.get_var_name(),
            var_latex=self.get_var_name(),
        )

    def get_file_prefix(self) -> str:
        return self.prefix

    def get_var_name(self) -> str:
        return "f"

    def get_name_fragments(self) -> list[str]:
        return [self.prefix] + self.var_names
