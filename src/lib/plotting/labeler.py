from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from lib.plotting.plot_info import PlotInfo


@dataclass
class TreeLabeler:
    set_text: Callable[[str], None]
    source: PlotInfo | None = None

    children: list[TreeLabeler] = field(default_factory=list, init=False)
    parent: TreeLabeler | None = field(default=None, init=False)

    _subject: str | None = field(default=None, init=False)
    _sublabels: list[str] = field(default_factory=list, init=False)

    def add_child(self, child: TreeLabeler):
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
