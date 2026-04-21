from lib.data.data_with_attrs import LazyList

from .. import file_util, particle_util
from ..var_info_registry import lookup
from .source import DataSource


class ParticleLoader(DataSource):
    def __init__(self, prefix: file_util.ParticlePrefix, var_name: str | None, steps: list[int]):
        self.prefix = prefix
        self.var_name = var_name
        self.steps = steps

    def get_data(self) -> LazyList:
        df = particle_util.load_df(self.prefix, self.steps)

        var_info = {key: lookup(self.prefix, key) for key in df.dims}
        return df.assign_metadata(
            name_fragments=self.get_name_fragments(),
            var_name=self.var_name,
            var_info=var_info,
        )

    def get_name_fragments(self) -> list[str]:
        fragments = [self.prefix]
        if self.var_name is not None:
            fragments.append(self.var_name)
        return fragments
