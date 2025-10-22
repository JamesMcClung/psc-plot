import argparse
import typing

from .. import bp_util
from ..animation import Animation, BpAnimation
from ..dimension import DIMENSIONS
from ..file_util import BP_PREFIXES
from ..plugins import PLUGINS_BP, PluginBp
from ..plugins.plugins_bp.fourier import Fourier
from . import args_base

__all__ = ["add_subparsers_bp", "ArgsBp"]

type Scale = typing.Literal["linear", "log", "loglog"]
SCALES: list[Scale] = list(Scale.__value__.__args__)


class ArgsBp(args_base.ArgsTyped):
    variable: str
    versus: list[str]
    scale: Scale
    plugins: list[PluginBp]

    @property
    def save_name(self) -> str:
        versus = ",".join(self.versus)
        plugin_name_fragments = "".join(filter(lambda nf: nf != "", ("-" + p.get_name_fragment() for p in self.plugins)))
        return f"{self.prefix}-{self.variable}-vs_{versus}{plugin_name_fragments}.mp4"

    def get_animation(self) -> Animation:
        steps = bp_util.get_available_steps_bp(self.prefix)

        for dim_name in self.versus:
            dim = DIMENSIONS[dim_name]
            if dim.is_fourier():
                # implicitly add a Fourier plugin if not already present
                for plugin in self.plugins:
                    if isinstance(plugin, Fourier) and plugin.dim_name == dim.name:
                        break
                else:
                    # TODO make versus its own plugin (or plugin package?)
                    self.plugins.insert(0, Fourier(dim.toggle_fourier().name))

        anim = BpAnimation.get_animation(steps, self.prefix, self.variable, self.plugins, self.versus)

        if self.scale == "linear":
            anim.set_scale("linear", "linear")
        elif self.scale == "log":
            anim.set_scale("linear", "log")
        elif self.scale == "loglog":
            anim.set_scale("log", "log")

        return anim


def add_subparsers_bp(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(ArgsBp)
    parent.add_argument("variable", type=str, help="the variable to plot")

    for plugin_adder in PLUGINS_BP:
        plugin_adder.add_to(parent)

    parent.add_argument(
        "--versus",
        "-v",
        nargs="+",
        type=str,
        choices=DIMENSIONS.keys(),
        default=["y", "z"],
        help="plot against these dimensions, averaging over others",
    )

    parent.add_argument(
        "--scale",
        choices=SCALES,
        default="linear",
        help="use this scale",
    )

    # may have to unroll this loop later when e.g. different prefixes have different derived variables
    for bp_prefix in BP_PREFIXES:
        subparsers.add_parser(bp_prefix, parents=[parent])
