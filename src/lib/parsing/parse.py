import argparse
from pathlib import Path

from lib.config import CONFIG
from lib.data.loader_registry import discover_all
from lib.parsing.args import Args
from lib.parsing.args_registry import CUSTOM_ARGS


def _get_parser() -> tuple[argparse.ArgumentParser, dict]:
    discoveries = discover_all(CONFIG.data_dir)

    parser = argparse.ArgumentParser(prog="psc-plot")

    parser.add_argument("prefix", choices=discoveries.keys(), help="data file prefix (auto-discovered from the data directory)")
    parser.add_argument("variable", nargs="?", default=None, help="field variable to work with")
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

    for custom_arg in CUSTOM_ARGS:
        custom_arg.add_to(parser)

    return parser, discoveries


def get_parsed_args(args: list[str] | None = None) -> Args:
    parser, discoveries = _get_parser()
    args = parser.parse_args(args, namespace=Args())
    args.loader = discoveries[args.prefix](args.prefix, active_key=args.variable)
    return args
