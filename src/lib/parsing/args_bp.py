import argparse

from .. import bp_util
from ..animation import Animation, BpAnimation1d, BpAnimation2d
from ..bp_util import BP_DIMS, BpDim
from ..file_util import BP_PREFIXES
from ..plugins import PLUGINS_BP, PluginBp
from . import args_base

__all__ = ["add_subparsers_bp", "ArgsBp"]


class ArgsBp(args_base.ArgsTyped):
    variable: str
    versus_1d: BpDim | None
    versus_2d: tuple[BpDim, BpDim] | None
    plugins: list[PluginBp]

    @property
    def save_name(self) -> str:
        versus = self.versus_1d if self.versus_1d else "".join(self.versus_2d)
        plugin_name_fragments = "".join(filter(lambda nf: nf != "", ("-" + p.get_name_fragment() for p in self.plugins)))
        return f"{self.prefix}-{self.variable}-vs_{versus}{plugin_name_fragments}.mp4"

    def get_animation(self) -> Animation:
        steps = bp_util.get_available_steps_bp(self.prefix)

        if self.versus_1d:
            anim = BpAnimation1d(steps, self.prefix, self.variable, self.versus_1d)
        else:
            anim = BpAnimation2d(steps, self.prefix, self.variable, self.versus_2d)

        for plugin in self.plugins:
            anim.add_plugin(plugin)

        return anim


def add_subparsers_bp(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(ArgsBp)
    parent.add_argument("variable", type=str, help="the variable to plot")

    for kwargs in PLUGINS_BP:
        parent.add_argument(
            *kwargs.name_or_flags,
            type=kwargs.type,
            dest="plugins",
            action="append",
            metavar=kwargs.metavar,
            help=kwargs.help,
        )
    parent.set_defaults(plugins=[])

    versus_group = parent.add_mutually_exclusive_group()
    versus_group.add_argument(
        "--versus-1d",
        type=str,
        choices=BP_DIMS,
        help="plot the variable against this dimension as a line plot, averaging over other dimensions",
    )
    versus_group.add_argument(
        "--versus-2d",
        nargs=2,
        type=str,
        choices=BP_DIMS,
        default=("y", "z"),
        help="plot the variable against these dimensions as a heat map, averaging over the third dimension",
    )

    # may have to unroll this loop later when e.g. different prefixes have different derived variables
    for bp_prefix in BP_PREFIXES:
        subparsers.add_parser(bp_prefix, parents=[parent])
