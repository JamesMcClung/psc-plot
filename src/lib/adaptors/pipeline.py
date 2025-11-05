import xarray as xr

from .adaptor_base import Adaptor, FieldAdaptor


class Pipeline[Data, AdaptorType: Adaptor[Data]]:
    def __init__(self, *adaptors: AdaptorType):
        self.adaptors = list(adaptors)

    def get_name_fragments(self) -> list[str]:
        name_fragments = [adaptor.get_name_fragment() for adaptor in self.adaptors]
        name_fragments = [frag for frag in name_fragments if frag]
        return name_fragments

    def apply(self, da: Data) -> Data:
        for adaptor in self.adaptors:
            da = adaptor.apply(da)
        return da


class FieldPipeline(Pipeline[xr.DataArray, FieldAdaptor]):
    def get_modified_dep_var_name(self, dep_var_name: str) -> str:
        for adaptor in self.adaptors:
            dep_var_name = adaptor.get_modified_dep_var_name(dep_var_name)
        return dep_var_name
