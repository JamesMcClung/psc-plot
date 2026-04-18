import argparse
from pathlib import Path

from lib.data.adaptor import Adaptor
from lib.data.compile import compile_source
from lib.data.field_loader import FieldLoader
from lib.data.particle_loader import ParticleLoader
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook
from lib.plotting.plot import Plot

from .. import field_util, particle_util
from ..file_util import FIELD_PREFIXES, PARTICLE_PREFIXES, Prefix


class Args(argparse.Namespace):
    prefix: Prefix
    variable: str | None
    adaptors: list[Adaptor]
    hooks: list[Hook]
    show: bool
    save: Path | None
    save_format: str | None

    def get_animation(self) -> Plot:
        if self.prefix in FIELD_PREFIXES:
            steps = field_util.get_available_field_steps(self.prefix)
            loader = FieldLoader(self.prefix, self.variable, steps)
        elif self.prefix in PARTICLE_PREFIXES:
            steps = particle_util.get_available_particle_steps(self.prefix)
            loader = ParticleLoader(self.prefix, steps)
        else:
            raise ValueError(f"Unknown prefix: {self.prefix}")

        source = compile_source(loader, self.adaptors)
        data = source.get_data()

        plot = get_plot(data)

        for hook in self.hooks:
            plot.add_hook(hook)

        return plot
