from __future__ import annotations

import dask.dataframe as dd
import pandas as pd
import xarray as xr

from lib.data.data_with_attrs import DataWithAttrs, Field, List, Metadata


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
    """Wraps `apply` to perform standard metadata mutations."""

    def get_modified_display_latex(self, metadata: Metadata) -> str:
        if metadata.var_name is not None and metadata.var_name in metadata.var_info:
            return metadata.active_var_info.name.latex
        return metadata.display_latex

    def get_modified_unit_latex(self, metadata: Metadata) -> str:
        if metadata.var_name is not None and metadata.var_name in metadata.var_info:
            return metadata.active_var_info.unit.latex
        return metadata.unit_latex

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        data = super().apply(data)

        name_fragments = data.metadata.name_fragments + self.get_name_fragments()
        display_latex = self.get_modified_display_latex(data.metadata)
        unit_latex = self.get_modified_unit_latex(data.metadata)

        var_info = data.metadata.var_info
        if data.metadata.var_name is not None and var_info:
            from dataclasses import replace as _replace
            from lib.latex import Latex
            old_dim = var_info.get(data.metadata.var_name)
            if old_dim is not None:
                new_dim = _replace(old_dim, name=Latex(display_latex), unit=Latex(unit_latex))
                var_info = {**var_info, data.metadata.var_name: new_dim}

        return data.assign_metadata(
            name_fragments=name_fragments,
            display_latex=display_latex,
            unit_latex=unit_latex,
            var_info=var_info,
        )


class BareAdaptor(MetadataAdaptor):
    """An adaptor that works with the raw data, no metadata required."""

    def apply_field(self, data: Field) -> DataWithAttrs:
        return data.with_active_data(self.apply_field_bare(data.active_data))

    def apply_list(self, data: List) -> DataWithAttrs:
        return data.with_active_data(self.apply_list_bare(data.active_data))

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        _fail_apply_field(self.__class__)

    def apply_list_bare(self, series: pd.Series | dd.Series) -> pd.Series | dd.Series:
        _fail_apply_list(self.__class__)
