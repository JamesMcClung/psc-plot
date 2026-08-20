from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

from lib.data.types import VarKey
from lib.plotting.plot_info import PlotInfo, PlotInfo2D, PlotInfoColor, PlotInfoMaybeColor
from lib.plotting.renderer2 import Renderer2


@dataclass
class Labeler(Renderer2):
    set_text: Callable[[str], None]


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

    def update(self):
        """Propagate updates up to the root labeler, which makes sure that everyone rebuilds and then everyone updates text."""
        if self.parent:
            return self.parent.update()
        else:
            self._rebuild()
            self._update_text()

    def _rebuild(self):
        for child in self.children:
            child._rebuild()

        child_subjects = {child._subject for child in self.children}
        all_child_sublabels = {sublabel: None for child in self.children for sublabel in child._sublabels}  # use dict to preserve insertion order
        common_child_sublabels = {sublabel: None for sublabel in all_child_sublabels if all(sublabel in child._sublabels for child in self.children)}  # use dict to preserve insertion order

        if self.source:
            self._subject = self.source.subject
            self._sublabels = self.source.get_sublabels()

            # only eliminate child subjects + sublabels if every child shares the root subject and all its sublabels
            has_common_subject = {self._subject} == child_subjects
            has_common_sublabels = set(self._sublabels) <= set(common_child_sublabels.keys())

            if has_common_subject and has_common_sublabels:
                self._eliminate_subject()
                self._eliminate_common_sublabels()

        else:
            # no source -> lift all common subject and/or sublabels independently

            if len(child_subjects) == 1:
                self._subject = child_subjects.pop()
                self._eliminate_subject()
            else:
                self._subject = None

            self._sublabels = list(common_child_sublabels.keys())
            self._eliminate_common_sublabels()

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

    def _eliminate_subject(self):
        for child in self.children:
            child._subject = None

    def _eliminate_common_sublabels(self):
        for child in self.children:
            for sublabel in self._sublabels:
                child._sublabels.remove(sublabel)


@dataclass
class UnitLabeler(Labeler):
    axis_name: Literal["x", "y", "color"]
    sources: list[PlotInfo] = field(default_factory=list)

    require_display_match: bool = field(kw_only=True, default=True)
    """If false, sources only have to agree on the unit. Otherwise, all sources must agree on display and unit."""

    def update(self):
        self.set_text(self._get_label())

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

        labels = {info.get_dim_label(key) for info, key in zip(self.sources, keys)}
        if len(labels) == 1:
            return labels.pop()

        if self.require_display_match:
            raise ValueError(f"{self.axis_name} labels must all be the same, but found {labels}")

        units = {info.dim_units[key].maybe_with_dollars() for info, key in zip(self.sources, keys)}
        if len(units) == 1:
            return units.pop()

        raise ValueError(f"{self.axis_name} units must all be the same, but found {units}")


@dataclass(init=False)
class SubjectAndUnitLabeler(Labeler):
    def __init__(self, set_text: Callable[[str], None], axis_name: Literal["x", "y", "color"], source: PlotInfo):
        super().__init__(set_text)
        self._subject = ""
        self._unit = ""

        self.subject_labeler = SubjectLabeler(self._set_subject, source)
        self.unit_labeler = UnitLabeler(self._set_unit, axis_name, [source])

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
