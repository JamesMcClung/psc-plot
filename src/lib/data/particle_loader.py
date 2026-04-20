from lib.data.data_with_attrs import LazyList
from lib.dimension import get_default_dim

from .. import field_units, file_util, particle_util
from .source import DataSource


class ParticleLoader(DataSource):
    def __init__(self, prefix: file_util.ParticlePrefix, var_name: str | None, steps: list[int]):
        self.prefix = prefix
        self.var_name = var_name
        self.steps = steps

    def get_data(self) -> LazyList:
        df = particle_util.load_df(self.prefix, self.steps)

        if self.var_name is not None:
            info = field_units.lookup_particle(self.var_name)
            display_latex = info.display_latex
            unit_latex = info.unit_latex
        else:
            display_latex = None
            unit_latex = None

        dims = {key: get_default_dim(key) for key in df.dims}
        return df.assign_metadata(
            name_fragments=self.get_name_fragments(),
            var_name=self.var_name,
            display_latex=display_latex,
            unit_latex=unit_latex,
            dims=dims,
        )

    def get_file_prefix(self) -> str:
        return self.prefix

    def get_name_fragments(self) -> list[str]:
        fragments = [self.prefix]
        if self.var_name is not None:
            fragments.append(self.var_name)
        return fragments
