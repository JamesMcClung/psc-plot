from lib.data.data_with_attrs import DataWithAttrs, Field, List
from lib.derived_field_variables.derived_field_variable import derive_field_variable
from lib.derived_particle_variables.derived_particle_variable import derive_particle_variable
from lib.file_util import Prepath, split_prepath


def ensure_derived[D: DataWithAttrs](data: D, prepath: Prepath, key: str) -> D:
    _, prefix = split_prepath(prepath)
    if isinstance(data, Field):
        return derive_field_variable(data, key, prefix)
    elif isinstance(data, List):
        return derive_particle_variable(data, key, prefix)
    else:
        raise TypeError(data.__class__)
