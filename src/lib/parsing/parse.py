import argparse
from pathlib import Path

from lib.parsing.args import Args
from lib.parsing.args_registry import CUSTOM_ARGS

from ..file_util import FIELD_PREFIXES, PARTICLE_PREFIXES


def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="psc-plot")

    parser.add_argument("prefix", choices=FIELD_PREFIXES + PARTICLE_PREFIXES, help="data file prefix")
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

    return parser


def get_parsed_args() -> Args:
    parser = _get_parser()
    return parser.parse_args(namespace=Args())
