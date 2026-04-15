from lib.data.data_with_attrs import LazyList

from .. import field_units, file_util, particle_util
from .source import DataSource


class ParticleLoader(DataSource):
    def __init__(self, prefix: file_util.ParticlePrefix, steps: list[int]):
        self.prefix = prefix
        self.steps = steps

    def get_data(self) -> LazyList:
        df = particle_util.load_df(self.prefix, self.steps)

        info = field_units.lookup_particle(self.get_var_name())
        return df.assign_metadata(
            name_fragments=self.get_name_fragments(),
            var_name=self.get_var_name(),
            display_latex=info.display_latex,
            unit_latex=info.unit_latex,
        )

    def get_file_prefix(self) -> str:
        return self.prefix

    def get_var_name(self) -> str:
        return "f"

    def get_name_fragments(self) -> list[str]:
        return [self.prefix]
