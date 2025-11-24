from __future__ import annotations

import typing
from abc import abstractmethod

from .compatability import ensure_type
from .keys import VAR_LATEX_KEY


class Adaptor:
    @abstractmethod
    def apply(self, data: typing.Any) -> typing.Any: ...

    def get_name_fragments(self) -> list[str]:
        return []


class AtomicAdaptor(Adaptor):
    allowed_types: list[type]

    @abstractmethod
    def apply_atomic(self, data: typing.Any) -> typing.Any:
        """Transform the data, but don't change the latex-formatted var string."""

    def get_modified_var_latex(self, var_latex: str) -> str:
        return var_latex

    def apply(self, data: typing.Any) -> typing.Any:
        ensure_type(self.__class__.__name__, data, *self.allowed_types)
        var_latex = data.attrs[VAR_LATEX_KEY]
        data = self.apply_atomic(data)
        data.attrs[VAR_LATEX_KEY] = self.get_modified_var_latex(var_latex)
        return data
