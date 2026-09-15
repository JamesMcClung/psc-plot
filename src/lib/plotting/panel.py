from dataclasses import dataclass, field

from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.colorbar import Colorbar
from matplotlib.text import Text

from lib.plotting.axis_id import AxisId
from lib.plotting.data_setter import DataSetter
from lib.plotting.labeler import Labeler, SubjectAndUnitLabeler, SubjectLabeler, UnitLabeler
from lib.plotting.plot_info import PlotInfo, PlotInfo2D, PlotInfoColor


@dataclass
class Panel:
    title_labeler: SubjectLabeler | None = field(init=False, default=None)
    legend_labelers_per_axes: dict[Axes, list[SubjectLabeler]] = field(init=False, default_factory=dict)
    cbar_labeler: Labeler | None = field(init=False, default=None)
    data_setters: list[DataSetter] = field(init=False, default_factory=list)
    units_per_axis_per_axes: dict[Axes, dict[AxisId, UnitLabeler]] = field(init=False, default_factory=dict)

    def update_data(self):
        for data_setter in self.data_setters:
            data_setter.update()

    def update_labels(self):
        for labeler in self.get_labelers():
            labeler.update()

        for axes, labelers in self.legend_labelers_per_axes.items():
            if not any(labeler._get_label() for labeler in labelers):
                if legend := axes.get_legend():
                    legend.remove()
            else:
                axes.legend()  # required for label redraw

    def get_labelers(self) -> list[Labeler]:
        maybe_labelers = [
            self.title_labeler,
            self.cbar_labeler,
            *(legend_labeler for labelers in self.legend_labelers_per_axes.values() for legend_labeler in labelers),
            *(unit_labeler for units_per_axis in self.units_per_axis_per_axes.values() for unit_labeler in units_per_axis.values()),
        ]
        return [labeler for labeler in maybe_labelers if labeler]

    def get_subject_labelers(self, *, toplevel_only: bool = False) -> list[SubjectLabeler]:
        subject_labelers: list[SubjectLabeler] = []

        for labeler in self.get_labelers():
            if isinstance(labeler, SubjectLabeler):
                subject_labelers.append(labeler)
            elif isinstance(labeler, SubjectAndUnitLabeler):
                subject_labelers.append(labeler.subject_labeler)

        if toplevel_only:
            return [labeler for labeler in subject_labelers if labeler.parent is None]
        return subject_labelers

    def wire_title(self, title: Text, info: PlotInfo | None = None):
        self.title_labeler = SubjectLabeler(title.set_text, info)
        for legend_labelers in self.legend_labelers_per_axes.values():
            for legend_labeler in legend_labelers:
                self.title_labeler.add_child(legend_labeler)
        if self.cbar_labeler and isinstance(self.cbar_labeler, SubjectAndUnitLabeler):
            self.title_labeler.add_child(self.cbar_labeler.subject_labeler)

    def wire_legend_label(self, artist: Artist, info: PlotInfo):
        legend_labeler = SubjectLabeler(artist.set_label, info)

        axes = artist.axes
        assert axes is not None
        self.legend_labelers_per_axes.setdefault(axes, []).append(legend_labeler)

        if self.title_labeler:
            self.title_labeler.add_child(legend_labeler)

    def wire_cbar_label(self, cbar: Colorbar, info: PlotInfoColor):
        is_subject = info.dim_displays[info.color_dim].maybe_with_dollars() == info.subject
        if is_subject:
            self.cbar_labeler = SubjectAndUnitLabeler(cbar.set_label, "color", info)
            if self.title_labeler:
                self.title_labeler.add_child(self.cbar_labeler.subject_labeler)
        else:
            self.cbar_labeler = UnitLabeler(cbar.set_label, "color", [info])

    def wire_data_setter(self, data_setter: DataSetter):
        self.data_setters.append(data_setter)

    def wire_units(self, ax: Axes, axis_id: AxisId, infos: list[PlotInfo2D], *, require_display_match: bool = True):
        units_per_axis = self.units_per_axis_per_axes.setdefault(ax, {})
        if labeler := units_per_axis.get(axis_id):
            labeler.sources.extend(infos)
            labeler.require_display_match = require_display_match
        else:
            set_label = {"x": ax.set_xlabel, "y": ax.set_ylabel}[axis_id]
            units_per_axis[axis_id] = UnitLabeler(set_label, axis_id, infos, require_display_match=require_display_match)
