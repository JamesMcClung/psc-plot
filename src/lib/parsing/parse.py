import argparse
import shlex

from lib.data.adaptor import WorldAdaptor
from lib.data.adaptors.versus import Versus
from lib.data.adaptors.with_ import WITH_FORMAT, parse_initial_with
from lib.parsing.args import Args
from lib.parsing.args_registry import CUSTOM_ARGS, get_store_combined_args_action
from lib.parsing.parse_save import SAVE_METAVAR, parse_save


def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="psc-plot")

    parser.add_argument(
        help="initial active prepath and variable (identical to --with)",
        nargs="*",
        metavar=WITH_FORMAT,
        type=parse_initial_with,
        dest="adaptors",
        action="extend",
    )
    parser.add_argument(
        "-s",
        "--save",
        action=get_store_combined_args_action(parse_save),
        dest="save",
        metavar=SAVE_METAVAR,
        nargs="*",
        default=None,
        help="save the figure. Each argument is either a path fragment '[dir/][stem][.ext]' or one of 'dir=<dir>', 'name=<stem>', 'format=<ext>'. With no arguments, saves to the current directory using a filename derived from the pipeline and the default format for the data. A bare fragment naming a directory must end in '/' (or use dir=), otherwise it is taken as the filename stem.",
    )
    parser.add_argument("-q", "--quiet", action="store_false", dest="show", help="don't show the figure")
    parser.add_argument(
        "--save-dpi",
        type=float,
        default=None,
        help="dots per inch of saved figure (defaults to Matplotlib's default)",
    )
    # --dask-graph renders no plot, so there'd be nothing for --profile to time
    profile_or_dask_graph = parser.add_mutually_exclusive_group()
    profile_or_dask_graph.add_argument(
        "--dask-graph",
        action="store_true",
        help="visualize the pipeline's dask graph as SVG instead of rendering a plot",
    )
    profile_or_dask_graph.add_argument(
        "--profile",
        action="store_true",
        help="report the environment, the resolved config, and the time and memory each pipeline stage takes. Never shows the figure: profiles --save if given, else renders every frame offscreen. With no pipeline, reports only the environment",
    )

    for custom_arg in CUSTOM_ARGS:
        custom_arg.add_to(parser)

    return parser


def parse_args(args_list: list[str] | None = None) -> Args:
    parser = _get_parser()
    return parser.parse_args(args_list, namespace=Args())


class StepParseError(ValueError): ...


class _RaisingArgumentParser(argparse.ArgumentParser):
    """Raise instead of printing usage and exiting, so a bad step becomes an ordinary exception."""

    def error(self, message):
        raise StepParseError(message)


def _get_steps_parser() -> argparse.ArgumentParser:
    parser = _RaisingArgumentParser(prog="pipeline step", add_help=False, allow_abbrev=False)
    for custom_arg in CUSTOM_ARGS:
        if custom_arg.dest == "adaptors":
            custom_arg.add_to(parser)
    return parser


def parse_steps(steps: list[str]) -> list[WorldAdaptor]:
    """Parse pipeline steps (each one CLI flag and its arguments, e.g. `"--recenter y=-"`) into adaptors.

    Only data adaptors are accepted: hooks, save/show flags, and positional prepaths are unrecognized, and `--versus` is rejected because the plot target it creates would be discarded.
    """
    parser = _get_steps_parser()
    adaptors: list[WorldAdaptor] = []
    for step in steps:
        try:
            # A fresh namespace per step: the combine-args action appends to whatever list it finds.
            namespace = parser.parse_args(shlex.split(step), namespace=argparse.Namespace(adaptors=[]))
        except StepParseError as e:
            raise StepParseError(f"step '{step}': {e}") from None
        for adaptor in namespace.adaptors:
            if isinstance(adaptor, Versus):
                raise StepParseError(f"step '{step}': --versus is not allowed in a pipeline step, since the plot target it creates would be discarded")
        adaptors.extend(namespace.adaptors)
    return adaptors
