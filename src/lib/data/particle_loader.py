from lib.data.data_with_attrs import LazyList

from .. import file_util, particle_util
from ..var_info_registry import lookup
from .source import DataSource


class ParticleLoader(DataSource):
    def __init__(self, prefix: file_util.ParticlePrefix, active_key: str | None, steps: list[int]):
        self.prefix = prefix
        self.active_key = active_key
        self.steps = steps

    def get_data(self) -> LazyList:
        df = particle_util.load_df(self.prefix, self.steps)

        var_infos = {key: lookup(self.prefix, key) for key in df.dims}
        return df.assign_metadata(
            name_fragments=self.get_name_fragments(),
            active_key=self.active_key,
            var_infos=var_infos,
        )

    def get_name_fragments(self) -> list[str]:
        fragments = [self.prefix]
        if self.active_key is not None:
            fragments.append(self.active_key)
        return fragments
