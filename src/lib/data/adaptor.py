import inspect
from abc import abstractmethod
from typing import Any

from lib.data.data_with_attrs import DataWithAttrs

from .compatability import ensure_type, get_allowed_types


class Adaptor:
    @abstractmethod
    def apply(self, data: DataWithAttrs) -> DataWithAttrs: ...

    def get_name_fragments(self) -> list[str]:
        return []


# TODO could make this generic to parameterize apply_atomic by input/output
# TODO rename this and apply_atomic, since it is no longer "atomic" (ie, no longer ignores metadata)
class CheckedAdaptor(Adaptor):
    @abstractmethod
    def apply_checked(self, data: DataWithAttrs) -> DataWithAttrs:
        """Transform the data and, if appropriate, metadata."""

    def get_modified_var_latex(self, var_latex: str) -> str:
        return var_latex

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        *_, apply_atomic_data_param = inspect.signature(self.apply_checked).parameters.values()
        allowed_types = get_allowed_types(apply_atomic_data_param.annotation)
        ensure_type(self.__class__.__name__, data, *allowed_types)

        data = self.apply_checked(data)

        name_fragments = data.metadata.name_fragments + self.get_name_fragments()
        var_latex = self.get_modified_var_latex(data.metadata.var_latex)

        return data.assign_metadata(name_fragments=name_fragments, var_latex=var_latex)


class BareAdaptor(CheckedAdaptor):
    @abstractmethod
    def apply_bare(self, data: Any) -> Any: ...

    def apply_checked(self, data: DataWithAttrs) -> DataWithAttrs:
        *_, apply_bare_data_param = inspect.signature(self.apply_bare).parameters.values()
        allowed_types = get_allowed_types(apply_bare_data_param.annotation)
        ensure_type(self.__class__.__name__, data.data, *allowed_types)

        return data.assign_data(self.apply_bare(data.data))
