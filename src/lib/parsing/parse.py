import argparse

from lib.data.adaptors.with_ import WITH_FORMAT, parse_with
from lib.parsing.args import Args
from lib.parsing.args_registry import CUSTOM_ARGS, get_store_combined_args_action
from lib.parsing.parse_save import SAVE_METAVAR, parse_save


def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="psc-plot")

    parser.add_argument(
        help="initial active prepath",
        nargs="?",
        metavar=WITH_FORMAT,
        type=parse_with,
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
    parser.add_argument(
        "--dask-graph",
        action="store_true",
        help="visualize the pipeline's dask graph as SVG instead of rendering a plot",
    )

    for custom_arg in CUSTOM_ARGS:
        custom_arg.add_to(parser)

    return parser


def parse_args(args_list: list[str] | None = None) -> Args:
    parser = _get_parser()
    return parser.parse_args(args_list, namespace=Args())
