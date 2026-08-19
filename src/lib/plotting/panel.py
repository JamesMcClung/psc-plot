from dataclasses import dataclass, field

from matplotlib.axes import Axes

from lib.plotting.labeler import TreeLabeler
from lib.plotting.renderer2 import Renderer2


@dataclass
class Panel:
    subject_labeler: TreeLabeler | None = field(init=False, default=None)
    data_setters: list[Renderer2] = field(init=False, default_factory=list)
