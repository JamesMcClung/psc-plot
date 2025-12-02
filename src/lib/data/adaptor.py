from __future__ import annotations

import inspect
import typing
from abc import abstractmethod

from lib.data.keys import NAME_FRAGMENTS_KEY, VAR_LATEX_KEY

from .compatability import ensure_type, get_allowed_types


class Adaptor:
    @abstractmethod
    def apply(self, data: typing.Any) -> typing.Any: ...

    def get_name_fragments(self) -> list[str]:
        return []


class AtomicAdaptor(Adaptor):
    @abstractmethod
    def apply_atomic(self, data: typing.Any) -> typing.Any:
        """Transform the data. Doesn't need to propagate existing attrs, but may assign new ones."""

    def get_modified_var_latex(self, var_latex: str) -> str:
        return var_latex

    def apply(self, data: typing.Any) -> typing.Any:
        *_, apply_atomic_data_param = inspect.signature(self.apply_atomic).parameters.values()
        allowed_types = get_allowed_types(apply_atomic_data_param.annotation)
        ensure_type(self.__class__.__name__, data, *allowed_types)

        attrs = data.attrs
        data = self.apply_atomic(data)
        data.attrs = attrs | data.attrs
        data.attrs[NAME_FRAGMENTS_KEY] = data.attrs.get(NAME_FRAGMENTS_KEY, []) + self.get_name_fragments()
        if VAR_LATEX_KEY in data.attrs:
            data.attrs[VAR_LATEX_KEY] = self.get_modified_var_latex(data.attrs[VAR_LATEX_KEY])
        return data
