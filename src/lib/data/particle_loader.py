from lib.data.data_with_attrs import LazyList

from .. import file_util, particle_util
from .source import DataSource


class ParticleLoader(DataSource):
    def __init__(self, prefix: file_util.ParticlePrefix, steps: list[int]):
        self.prefix = prefix
        self.steps = steps

    def get_data(self) -> LazyList:
        df = particle_util.load_df(self.prefix, self.steps)

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
        return [self.prefix]
