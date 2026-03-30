from __future__ import annotations

import dask.dataframe as dd
import pandas as pd
import xarray as xr

from lib.data.data_with_attrs import DataWithAttrs, Field, List


def _fail_apply_field(adaptor_type: type[Adaptor]):
    message = f"{adaptor_type.__module__}.{adaptor_type.__name__} does not accept list data. Try converting to a field with --bin."
    raise RuntimeError(message)


def _fail_apply_list(adaptor_type: type[Adaptor]):
    message = f"{adaptor_type.__module__}.{adaptor_type.__name__} does not accept field data. Try converting to a list with --scatter."
    raise RuntimeError(message)


class Adaptor:
    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        if isinstance(data, List):
            return self.apply_list(data)
        elif isinstance(data, Field):
            return self.apply_field(data)
        else:
            message = f"unrecognized data type: {data.__class__:r}"
            raise Exception(message)

    def apply_list(self, data: List) -> DataWithAttrs:
        _fail_apply_field(self.__class__)

    def apply_field(self, data: Field) -> DataWithAttrs:
        _fail_apply_list(self.__class__)

    def get_name_fragments(self) -> list[str]:
        return []


class MetadataAdaptor(Adaptor):
    def get_modified_var_latex(self, var_latex: str) -> str:
        return var_latex

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        data = super().apply(data)

        name_fragments = data.metadata.name_fragments + self.get_name_fragments()
        var_latex = self.get_modified_var_latex(data.metadata.var_latex)

        return data.assign_metadata(name_fragments=name_fragments, var_latex=var_latex)


class BareAdaptor(MetadataAdaptor):
    def apply_field(self, data: Field) -> DataWithAttrs:
        return data.assign_data(self.apply_field_bare(data.data))

    def apply_list(self, data: List) -> DataWithAttrs:
        return data.assign_data(self.apply_list_bare(data.data))

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        _fail_apply_field(self.__class__)

    def apply_list_bare(self, df: dd.DataFrame | pd.DataFrame) -> dd.DataFrame | pd.DataFrame:
        _fail_apply_list(self.__class__)
