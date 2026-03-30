from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, FullList, List
from lib.parsing.args_registry import const_arg


@const_arg(
    dest="adaptors",
    flags="--compute",
    help="force full computation of the data (recommended when possible for significant speed improvements)",
)
class Compute(MetadataAdaptor):
    def apply_list(self, data: List) -> FullList:
        return data.compute()

    def apply_field(self, data: Field) -> Field:
        return data.map_data(lambda da: da.compute())
