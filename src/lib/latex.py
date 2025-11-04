from __future__ import annotations

import re
from dataclasses import dataclass, field


def strip_latex(latex: str) -> str:
    plain = latex
    plain = re.sub(r"\\\w+\{(.*?)\}", lambda match: match[1], plain)
    plain = plain.replace("^{-1}", "^-1")
    plain = plain.replace("\\", "")
    return plain


@dataclass(frozen=True)
class Latex:
    latex: str
    plain: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "plain", strip_latex(self.latex))

    def starts_with(self, latex: str) -> bool:
        return self.latex.startswith(latex)

    def ends_with(self, latex: str) -> bool:
        return self.latex.endswith(latex)

    def replace(self, old_latex: str, new_latex: str) -> Latex:
        return Latex(self.latex.replace(old_latex, new_latex))

    def remove_prefix(self, latex: str) -> Latex:
        return Latex(self.latex.removeprefix(latex))

    def remove_suffix(self, latex: str) -> Latex:
        return Latex(self.latex.removesuffix(latex))

    def prepend(self, latex: str) -> Latex:
        return Latex(latex + self.latex)

    def append(self, latex: str) -> Latex:
        return Latex(self.latex + latex)
