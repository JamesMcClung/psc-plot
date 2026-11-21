import argparse
import re

from lib.plotting.layout.options import FigSizeSpec

FIGSIZE_METAVAR = "W,H"

_SIDE = re.compile(r"(?P<number>\d+(\.\d*)?|\.\d+)(in)?")


def _parse_side(side: str, arg: str) -> float | None:
    if side == "auto":
        return None

    match = _SIDE.fullmatch(side)
    if not match or (inches := float(match["number"])) <= 0:
        raise argparse.ArgumentTypeError(f"expected each side of {FIGSIZE_METAVAR} to be 'auto' or a positive size in inches (e.g. '4' or '4in'), got '{side}' in '{arg}'")
    return inches


def parse_figsize(arg: str) -> FigSizeSpec:
    """`auto`, or `W,H`, where each side is `auto` or a positive number of inches with an optional `in` suffix."""
    if arg == "auto":
        return FigSizeSpec(None, None)

    sides = arg.split(",")
    if len(sides) != 2:
        raise argparse.ArgumentTypeError(f"expected 'auto' or {FIGSIZE_METAVAR}, got '{arg}'")

    width, height = (_parse_side(side, arg) for side in sides)
    return FigSizeSpec(width, height)
