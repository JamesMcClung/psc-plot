import argparse
from pathlib import Path

from lib.config import CONFIG
from lib.data.loader import discover_loaders
from lib.parsing.args import Args
from lib.parsing.args_registry import CUSTOM_ARGS


def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="psc-plot")

    parser.add_argument("prefix", help="initial active prefix")
    parser.add_argument("variable", nargs="?", default=None, help="initial active variable")
    parser.add_argument(
        "-s",
        "--save",
        action="store",
        metavar="dir",
        nargs="?",
        default=None,
        const=".",
        help="save the figure (to the given dir, if present)",
        type=Path,
    )
    parser.add_argument("-q", "--quiet", action="store_false", dest="show", help="don't show the figure")
    parser.add_argument(
        "--save-format",
        choices=["mp4", "gif"],
        default=None,
        help="format for saved animations (default: mp4, falls back to gif if ffmpeg unavailable)",
    )
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


def get_parsed_args(args_list: list[str] | None = None) -> Args:
    parser = _get_parser()
    args = parser.parse_args(args_list, namespace=Args())
    prefix_to_loader = discover_loaders(CONFIG.data_dir)
    args.loader = prefix_to_loader[args.prefix](args.prefix, active_key=args.variable)
    return args
