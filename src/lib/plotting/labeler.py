from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Literal

from lib.data.types import VarKey
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
    components propagate from the leaves to the root."""

    source: PlotInfo | None = None

    children: list[SubjectLabeler] = field(default_factory=list, init=False)
    parent: SubjectLabeler | None = field(default=None, init=False)

    _subject: str | None = field(default=None, init=False)
    _sublabels: list[str] = field(default_factory=list, init=False)

    def add_child(self, child: SubjectLabeler):
        assert child.parent is None
        child.parent = self
        self.children.append(child)

    def remove_from_tree(self):
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
        else:
            self._rebuild()
            self._update_text()

    def _rebuild(self):
        """Recompute this node's subject and sublabels. A leaf reads them from its source; any other node factors
        out whatever its children have in common."""
        for child in self.children:
            child._rebuild()

        if self.source:
            assert not self.children, "a labeler with a source is a leaf"
            self._subject = self.source.subject
            self._sublabels = self.source.get_sublabels()
            return

        children = self._get_children_labeling_data()

        self._subject = _get_common_subject(children)
        if self._subject is not None:
            for child in children:
                child._lift_subject()

        self._sublabels = _get_common_sublabels(children)
        for child in children:
            child._lift_sublabels(self._sublabels)

    def _get_children_labeling_data(self) -> list[SubjectLabeler]:
        return [child for child in self.children if child._labels_any_data()]

    # What a parent sees of this node, and what happens when the parent factors it out. Subclasses override these
    # to control how they take part in factoring.

    def _labels_any_data(self) -> bool:
        """Whether this node labels any data at all. A parent ignores one that doesn't, rather than taking it to
        offer no subject and no sublabels, which would stop anything being lifted from its siblings."""
        return self.source is not None or bool(self._get_children_labeling_data())

    def _get_liftable_subject(self) -> str | None:
        return self._subject

    def _lift_subject(self):
        self._subject = None

    def _get_liftable_sublabels(self) -> list[str]:
        return self._sublabels

    def _lift_sublabels(self, sublabels: list[str]):
        self._sublabels = [sublabel for sublabel in self._sublabels if sublabel not in sublabels]

    def _update_text(self):
        # set_text intelligently checks if the text actually changes or not
        self.set_text(self._get_label())
        for child in self.children:
            child._update_text()

    def _get_label(self) -> str:
        sublabels = ", ".join(self._sublabels)

        if self._subject and sublabels:
            return f"{self._subject} ({sublabels})"
        return self._subject or sublabels


def _get_common_subject(labelers: list[SubjectLabeler]) -> str | None:
    """The subject every labeler offers, if they agree on one."""
    subjects = {labeler._get_liftable_subject() for labeler in labelers}
    return subjects.pop() if len(subjects) == 1 else None


def _get_common_sublabels(labelers: list[SubjectLabeler]) -> list[str]:
    """The sublabels every labeler offers, in order of first appearance."""
    sublabelss = [labeler._get_liftable_sublabels() for labeler in labelers]
    all_sublabels = {sublabel: None for sublabels in sublabelss for sublabel in sublabels}  # use dict to preserve insertion order
    return [sublabel for sublabel in all_sublabels if all(sublabel in sublabels for sublabels in sublabelss)]


@dataclass
class UnitLabeler(Labeler):
    axis_name: Literal["x", "y", "color"]
    sources: list[PlotInfo] = field(default_factory=list)

    include_display: bool = field(kw_only=True, default=True)
    """Include the display in the label. If false, show unit only. Independent of `require_display_match`."""
    require_display_match: bool = field(kw_only=True, default=True)
    """If false, sources only have to agree on the unit. Otherwise, all sources must agree on display and unit."""

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
        return len({info.dim_displays[self._get_key(info)] for info in self.sources}) == 1

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

        displays = {info.dim_displays[key] for info, key in zip(self.sources, keys)}
        if self.require_display_match and len(displays) > 1:
            raise ValueError(f"{self.axis_name} displays must all be the same, but found {displays}")

        units = {info.dim_units[key] for info, key in zip(self.sources, keys)}
        if len(units) > 1:
            raise ValueError(f"{self.axis_name} units must all be the same, but found {units}")

        display = displays.pop().maybe_with_dollars() if self.include_display and len(displays) == 1 else ""
        unit = units.pop().maybe_with_dollars() if len(units) == 1 else ""

        if display and unit:
            return f"{display} [{unit}]"
        return display or unit and f"[{unit}]"


@dataclass(init=False)
class SubjectAndUnitLabeler(Labeler):
    def __init__(self, set_text: Callable[[str], None], axis_name: Literal["x", "y", "color"], source: PlotInfo):
        super().__init__(set_text)
        self._subject = ""
        self._unit = ""

        self.subject_labeler = SubjectLabeler(self._set_subject, source)
        self.unit_labeler = UnitLabeler(self._set_unit, axis_name, [source], include_display=False, require_display_match=False)

    def update(self):
        """Update sublabelers, which call `_set_subject` and/or `_set_unit` and thus `set_text` (twice, possibly)."""
        if self.subject_labeler:
            self.subject_labeler.update()

        if self.unit_labeler:
            self.unit_labeler.update()

    def _get_label(self) -> str:
        if self._subject and self._unit:
            return self._subject + " " + self._unit
        return self._subject or self._unit

    def _set_subject(self, subject: str):
        """Intended to be passed to a `SubjectLabeler`."""
        self._subject = subject
        self.set_text(self._get_label())

    def _set_unit(self, unit: str):
        """Intended to be passed to a `UnitLabeler`."""
        self._unit = unit
        self.set_text(self._get_label())


@dataclass(init=False)
class YAxisLabeler(SubjectLabeler):
    """Labels a y axis, `display [unit]`, as a `UnitLabeler` would. It also takes part in the subject tree: its
    children are the legend entries of the lines whose subject is their y dim. When the axis shows that display, it
    absorbs their subject, which then appears nowhere else. Sublabels just pass through it, since it can't show them."""

    def __init__(self, set_text: Callable[[str], None]):
        super().__init__(set_text)
        self.unit_labeler = UnitLabeler(set_text, "y", require_display_match=False)
        self._absorbs_subject = False

    def is_compatible(self, info: PlotInfo2D) -> bool:
        return self.unit_labeler.is_compatible(info)

    def add_source(self, info: PlotInfo2D):
        self.unit_labeler.sources.append(info)

    def _rebuild(self):
        for child in self.children:
            child._rebuild()

        children = self._get_children_labeling_data()
        # Every child's subject is the display of its y dim, so if the axis shows a display, it's theirs.
        self._absorbs_subject = bool(children) and self.unit_labeler.has_common_display()
        if self._absorbs_subject:
            for child in children:
                child._lift_subject()

    def _get_label(self) -> str:
        return self.unit_labeler._get_label()

    def _get_liftable_subject(self) -> str | None:
        if self._absorbs_subject:
            return None
        return _get_common_subject(self._get_children_labeling_data())

    def _lift_subject(self):
        for child in self._get_children_labeling_data():
            child._lift_subject()

    def _get_liftable_sublabels(self) -> list[str]:
        return _get_common_sublabels(self._get_children_labeling_data())

    def _lift_sublabels(self, sublabels: list[str]):
        for child in self._get_children_labeling_data():
            child._lift_sublabels(sublabels)


@dataclass(init=False)
class ColorbarLabeler(SubjectLabeler):
    """Labels a colorbar whose color dim is its source's subject, `subject (sublabels) [unit]`. It keeps the subject
    rather than offering it up, since the colorbar is where the subject belongs."""

    def __init__(self, set_text: Callable[[str], None], source: PlotInfoColor):
        super().__init__(set_text, source)
        self.unit_labeler = UnitLabeler(set_text, "color", [source], include_display=False)

    def _get_label(self) -> str:
        return " ".join(label for label in [super()._get_label(), self.unit_labeler._get_label()] if label)

    def _get_liftable_subject(self) -> str | None:
        return None
