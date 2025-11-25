from __future__ import annotations

import inspect
import types
import typing
from abc import abstractmethod

from lib.data.keys import NAME_FRAGMENTS_KEY

from .compatability import ensure_type


class Adaptor:
    @abstractmethod
    def apply(self, data: typing.Any) -> typing.Any: ...

    def get_name_fragments(self) -> list[str]:
        return []


class AtomicAdaptor(Adaptor):
    @abstractmethod
    def apply_atomic(self, data: typing.Any) -> typing.Any:
        """Transform the data, but don't change the latex-formatted var string."""

    def get_modified_var_latex(self, var_latex: str) -> str:
        return var_latex

    def apply(self, data: typing.Any) -> typing.Any:
        *_, apply_atomic_data_param = inspect.signature(self.apply_atomic).parameters.values()
        apply_atomic_data_annotation = apply_atomic_data_param.annotation
        if isinstance(apply_atomic_data_annotation, type):
            allowed_types = [apply_atomic_data_annotation]
        if isinstance(apply_atomic_data_annotation, types.UnionType):
            allowed_types = apply_atomic_data_annotation.__args__
        ensure_type(self.__class__.__name__, data, *allowed_types)

        attrs = data.attrs
        data = self.apply_atomic(data)
        data.attrs = attrs
        data.attrs[NAME_FRAGMENTS_KEY] += self.get_name_fragments()
        return data
