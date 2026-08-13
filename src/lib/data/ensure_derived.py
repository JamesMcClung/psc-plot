from lib.data.data_with_attrs import DataWithAttrs, Field, List
from lib.data.types import SubdataKey
from lib.derived_field_variables.derived_field_variable import DERIVED_FIELD_VARIABLES, derive_field_variable
from lib.derived_particle_variables.derived_particle_variable import DERIVED_PARTICLE_VARIABLES, derive_particle_variable
from lib.file_util import split_prepath


def ensure_derived[D: DataWithAttrs](data: D, key: SubdataKey) -> D:
    _, prefix = split_prepath(data.metadata.prepath)
    if isinstance(data, Field):
        return derive_field_variable(data, key, prefix)
    elif isinstance(data, List):
        return derive_particle_variable(data, key, prefix)
    else:
        raise TypeError(data.__class__)


def get_derivable_keys(data: DataWithAttrs) -> list[SubdataKey]:
    _, prefix = split_prepath(data.metadata.prepath)
    if isinstance(data, Field):
        return list(DERIVED_FIELD_VARIABLES[prefix].keys())
    elif isinstance(data, List):
        return list(DERIVED_PARTICLE_VARIABLES[prefix].keys())
    else:
        raise TypeError(data.__class__)
