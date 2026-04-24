from lib.data.data_with_attrs import LazyList
from lib.data.source import DataSource


class ParticleLoaderBp(DataSource):
    """ADIOS2 particle loader — one instance per prt.<species_key> prefix.

    Registered dynamically by lib.parsing.parse._get_parser (not via @loader),
    because the set of valid prefixes depends on files present in the data
    directory at run time.
    """

    def __init__(self, prefix: str, active_key: str | None):
        self.prefix = prefix
        self.species_key = prefix.split(".", 1)[1]
        self.active_key = active_key

    def get_data(self) -> LazyList:
        raise NotImplementedError("implemented in Task 6")
