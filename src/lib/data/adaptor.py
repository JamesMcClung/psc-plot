from __future__ import annotations

import inspect
from abc import abstractmethod

from .compatability import ConsumesData, ProducesData
from .keys import VAR_LATEX_KEY


class Adaptor(ConsumesData, ProducesData):
    @abstractmethod
    def apply(self, data): ...

    def get_name_fragments(self) -> list[str]:
        return []

    def get_modified_var_latex(self, var_latex: str) -> str:
        return var_latex

    def get_input_data_type(self) -> type:
        *_, data_param = inspect.signature(self.apply).parameters.values()
        return data_param.annotation

    def get_output_data_type(self) -> type:
        return inspect.signature(self.apply).return_annotation


class AtomicAdaptor(Adaptor):
    @abstractmethod
    def apply_atomic(self, data):
        """Transform the data, but don't change the latex-formatted var string."""

    def apply(self, data):
        data = self.apply_atomic(data)
        data.attrs[VAR_LATEX_KEY] = self.get_modified_var_latex(data.attrs[VAR_LATEX_KEY])
        return data
