from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Literal

from lib.data.types import VarKey
from lib.latex import Latex
from lib.plotting.plot_info import PlotInfo, PlotInfo2D, PlotInfoColor, PlotInfoMaybeColor


@dataclass
class Labeler(ABC):
    set_text: Callable[[str], None]

    @abstractmethod
    def update(self): ...


@dataclass
class SubjectLabeler(Labeler):
    """Manages the subject labels associated with one or more datasets within a figure. A subject label comprises an
    optional subject (variable name) and any number of sublabels (e.g. scalar coordinates). When multiple datasets are
    plotted within the same figure, common label components can be "factored out" to a higher label location, e.g.
    from a legend to an axis title. Label locations are well-described by a tree structure, where common label
    components propagate from the leaves to the root.

    Sublabels are factored out by dim, and only if they agree on every frame, so that none moves between frames. The
    tree decides once, on its first update (or its first since it changed); each frame then just rebuilds the text."""

    source: PlotInfo | None = None

    children: list[SubjectLabeler] = field(default_factory=list, init=False)
    parent: SubjectLabeler | None = field(default=None, init=False)

    _subject: str | None = field(default=None, init=False)
    _sublabels: Sublabels = field(default_factory=dict, init=False)
    _decided: bool = field(default=False, init=False)
    """On the root: whether the tree has decided where everything goes."""

    def _root(self) -> SubjectLabeler:
        return self.parent._root() if self.parent else self

    def add_child(self, child: SubjectLabeler):
        assert child.parent is None
        self._root()._decided = False
        child.parent = self
        self.children.append(child)

    def remove_from_tree(self):
        self._root()._decided = False
        self._decided = False
        for child in self.children:
            child.parent = self.parent
        if self.parent is not None:
            self.parent.children.remove(self)
            self.parent.children.extend(self.children)
        self.children.clear()
        self.parent = None

    def update(self):
        """Propagate updates up to the root labeler, which makes sure that everyone rebuilds and then everyone updates text."""
        if self.parent:
            return self.parent.update()
        if not self._decided:
            self._rebuild()
            self._decided = True
        self._update_text()

    def _rebuild(self):
        """Recompute this node's subject and sublabels. A leaf reads them from its source; any other node factors
        out whatever its children have in common."""
        for child in self.children:
            child._rebuild()

        if self.source:
            assert not self.children, "a labeler with a source is a leaf"
            self._subject = self.source.subject
            self._sublabels = {dim: (texts, self.source) for dim, texts in self.source.get_frames_sublabels().items()}
            return

        children = self._get_children_labeling_data()

        self._subject = _get_common_subject(children)
        if self._subject is not None:
            for child in children:
                child._lift_subject()

        self._sublabels = _get_common_sublabels(children)
        for child in children:
            child._lift_sublabels(set(self._sublabels))

    def _get_children_labeling_data(self) -> list[SubjectLabeler]:
        return [child for child in self.children if child._labels_any_data()]

    # What a parent sees of this node, and what happens when the parent factors it out. Subclasses override these
    # to control how they take part in factoring.

    def _labels_any_data(self) -> bool:
        """A parent ignores children that don't, since their empty labels would block lifting from their siblings."""
        return self.source is not None or bool(self._get_children_labeling_data())

    def _get_liftable_subject(self) -> str | None:
        return self._subject

    def _lift_subject(self):
        self._subject = None

    def _get_liftable_sublabels(self) -> Sublabels:
        return self._sublabels

    def _lift_sublabels(self, dims: set[VarKey]):
        self._sublabels = {dim: sublabel for dim, sublabel in self._sublabels.items() if dim not in dims}

    def _update_text(self):
        # set_text intelligently checks if the text actually changes or not
        self.set_text(self._get_label())
        for child in self.children:
            child._update_text()

    def _get_label(self) -> str:
        # The current frame's text, from a source of each dim (all its sources agree, or it wouldn't be here).
        sublabels = ", ".join(source.get_coord_label(dim).maybe_with_dollars() for dim, (_, source) in self._sublabels.items() if dim in source.scalar_coord_values)

        if self._subject and sublabels:
            return f"{self._subject} ({sublabels})"
        return self._subject or sublabels


def _get_common_subject(labelers: list[SubjectLabeler]) -> str | None:
    """The subject every labeler offers, if they agree on one."""
    subjects = {labeler._get_liftable_subject() for labeler in labelers}
    return subjects.pop() if len(subjects) == 1 else None


type Sublabels = dict[VarKey, tuple[tuple[str, ...], PlotInfo]]
"""Sublabels by dim: the text on every frame, and a source whose current frame gives the text now."""


def _on_every_frame(texts: tuple[str, ...], n_frames: int) -> tuple[str, ...]:
    """`texts` over `n_frames` frames; a shorter sequence (e.g. a static plot's one frame) holds its last."""
    return tuple(texts[min(frame, len(texts) - 1)] for frame in range(n_frames))


def _get_common_sublabels(labelers: list[SubjectLabeler]) -> Sublabels:
    """The sublabels every labeler offers with the same text on every frame, in order of first appearance."""
    sublabelss = [labeler._get_liftable_sublabels() for labeler in labelers]
    dims = {dim: None for sublabels in sublabelss for dim in sublabels}  # use dict to preserve insertion order
    common = {}
    for dim in dims:
        if not all(dim in sublabels for sublabels in sublabelss):
            continue
        n_frames = max(len(sublabels[dim][0]) for sublabels in sublabelss)
        textss = {_on_every_frame(sublabels[dim][0], n_frames) for sublabels in sublabelss}
        if len(textss) == 1:
            [texts] = textss
            common[dim] = (texts, sublabelss[0][dim][1])
    return common


@dataclass
class UnitLabeler(Labeler):
    axis_name: Literal["x", "y", "color"]
    sources: list[PlotInfo] = field(default_factory=list)

    include_display: bool = field(kw_only=True, default=True)
    """Include the display in the label. If false, show unit only. Independent of `require_display_match`."""
    require_display_match: bool = field(kw_only=True, default=True)
    """If false, sources only have to agree on the unit. Otherwise, all sources must agree on display and unit."""
    line_break_before_unit: bool = field(kw_only=True, default=False)
    """Put the unit on a line of its own, below the display (for colorbars, whose text is horizontal and narrow)."""

    def update(self):
        self.set_text(self._get_label())

    def is_compatible(self, info: PlotInfo) -> bool:
        return self.are_compatible([info])

    def are_compatible(self, infos: list[PlotInfo]) -> bool:
        orig = self.sources
        self.sources = orig + infos
        try:
            self._get_label()
            return True
        except:
            return False
        finally:
            self.sources = orig

    def has_common_display(self) -> bool:
        """Whether the sources all agree on display, so that the label shows it."""
        return len(self._named_displays()) == 1

    def _named_displays(self) -> set[Latex]:
        """The sources' displays, except empty ones: those are unnamed (e.g. a --fit curve), so they defer to the others."""
        return {display for info in self.sources if (display := info.dim_displays[self._get_key(info)])}

    def _get_key(self, info: PlotInfo) -> VarKey:
        match self.axis_name:
            case "x":
                assert isinstance(info, PlotInfo2D)
                return info.x_dim
            case "y":
                assert isinstance(info, PlotInfo2D)
                return info.y_dim
            case "color":
                assert isinstance(info, (PlotInfoColor, PlotInfoMaybeColor)) and info.color_dim
                return info.color_dim

    def _get_label(self) -> str:
        keys = [self._get_key(info) for info in self.sources]

        displays = self._named_displays()
        if self.require_display_match and len(displays) > 1:
            raise ValueError(f"{self.axis_name} displays must all be the same, but found {displays}")

        units = {info.dim_units[key] for info, key in zip(self.sources, keys)}
        if len(units) > 1:
            raise ValueError(f"{self.axis_name} units must all be the same, but found {units}")

        display = displays.pop().maybe_with_dollars() if self.include_display and len(displays) == 1 else ""
        unit = units.pop().maybe_with_dollars() if len(units) == 1 else ""

        if display and unit:
            return f"{display}{'\n' if self.line_break_before_unit else ' '}[{unit}]"
        return display or unit and f"[{unit}]"


@dataclass(init=False)
class YAxisLabeler(SubjectLabeler):
    """Labels a y axis, `display [unit]`. Its children are the legend entries of lines whose subject is their y dim;
    when the axis shows a display, that is their subject, so it absorbs it. Sublabels pass through, since it can't
    show them."""

    def __init__(self, set_text: Callable[[str], None]):
        super().__init__(set_text)
        self.unit_labeler = UnitLabeler(set_text, "y", require_display_match=False)

    def is_compatible(self, info: PlotInfo2D) -> bool:
        return self.unit_labeler.is_compatible(info)

    def add_source(self, info: PlotInfo2D):
        self.unit_labeler.sources.append(info)

    def _rebuild(self):
        for child in self.children:
            child._rebuild()

        # Every child's subject is the display of its y dim, so if the axis shows a display, it's theirs.
        if self.unit_labeler.has_common_display():
            self._lift_subject()

    def _get_label(self) -> str:
        return self.unit_labeler._get_label()

    def _get_liftable_subject(self) -> str | None:
        return _get_common_subject(self._get_children_labeling_data())

    def _lift_subject(self):
        for child in self._get_children_labeling_data():
            child._lift_subject()

    def _get_liftable_sublabels(self) -> Sublabels:
        return _get_common_sublabels(self._get_children_labeling_data())

    def _lift_sublabels(self, dims: set[VarKey]):
        for child in self._get_children_labeling_data():
            child._lift_sublabels(dims)


@dataclass(init=False)
class ColorbarLabeler(SubjectLabeler):
    """Labels a colorbar whose color dim is its source's subject: `subject (sublabels)`, then `[unit]` on the line
    below. It keeps the subject rather than offering it up, since the colorbar is where the subject belongs."""

    def __init__(self, set_text: Callable[[str], None], source: PlotInfoColor):
        super().__init__(set_text, source)
        self.unit_labeler = UnitLabeler(set_text, "color", [source], include_display=False)

    def _get_label(self) -> str:
        return "\n".join(label for label in [super()._get_label(), self.unit_labeler._get_label()] if label)

    def _get_liftable_subject(self) -> str | None:
        return None
