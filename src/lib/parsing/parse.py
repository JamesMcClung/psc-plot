import argparse
import re
from pathlib import Path

from lib.config import CONFIG
from lib.data.loader_registry import LOADERS, register_loader
from lib.data.loaders.particle_bp import ParticleLoaderBp
from lib.parsing.args import Args
from lib.parsing.args_registry import CUSTOM_ARGS

_BP_PARTICLE_RE = re.compile(r"^prt\.([A-Za-z][A-Za-z0-9]*)\.\d+\.bp$")


def _register_bp_particle_prefixes() -> None:
    """Scan CONFIG.data_dir for prt.<key>.<step>.bp files and register a
    ParticleLoaderBp under each distinct prt.<key> prefix. Safe to call
    repeatedly; overwrites existing registrations for these prefixes."""
    if not CONFIG.data_dir.is_dir():
        return
    seen: set[str] = set()
    for entry in CONFIG.data_dir.iterdir():
        # BP "files" are actually directories; accept either.
        m = _BP_PARTICLE_RE.match(entry.name)
        if m is None:
            continue
        species_key = m.group(1)
        if species_key in seen:
            continue
        seen.add(species_key)
        register_loader(f"prt.{species_key}", ParticleLoaderBp)


def _get_parser() -> argparse.ArgumentParser:
    _register_bp_particle_prefixes()
    parser = argparse.ArgumentParser(prog="psc-plot")

    parser.add_argument("prefix", choices=LOADERS.keys(), help="data file prefix")
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
