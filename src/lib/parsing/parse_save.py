import argparse
from dataclasses import dataclass
from pathlib import Path

from lib.parsing import parse_util


@dataclass(frozen=True)
class SaveSpec:
    """The components of a save path, each None when the user did not specify it.
    Resolution of the defaults happens in SavePlotNode, which needs the Plot to
    decide a default format."""

    dir: Path | None = None
    name: str | None = None
    format: str | None = None


_KEYS = ("dir", "name", "format")

SAVE_METAVAR = "[dir/][stem][.ext] | dir=<dir> | name=<stem> | format=<ext>"


def _is_valid_stem(val: str) -> bool:
    """A stem must be nonempty and hold at least one non-'.' character, so that
    '.', '..' and friends fall through to being parsed as a dir."""
    return bool(val) and any(char != "." for char in val)


def _parse_dir(val: str) -> Path:
    """Expand a leading '~'. bash leaves it alone after a '=' (dir=~/figs) and
    inside quotes, so without this the save dir would be a literal '~'. A path
    like './~foo' normalizes to '~foo', which expanduser() rejects outright when
    no such user exists — keep it literal there, as os.path.expanduser does."""
    path = Path(val)
    try:
        return path.expanduser()
    except RuntimeError:
        return path


def _split_fragment(fragment: str) -> tuple[Path | None, str | None, str | None]:
    """Parse a bare '[dir/][stem][.ext]' fragment right-to-left, claiming each
    component only if it is valid. Returns (dir, stem, ext)."""
    rest = fragment

    # ext: text after the last "." that follows the last "/"; valid iff nonempty
    ext = None
    dot_idx = rest.rfind(".")
    if dot_idx > rest.rfind("/"):
        candidate = rest[dot_idx + 1 :]
        if candidate:
            ext = candidate
            rest = rest[:dot_idx]

    # stem: text after the last "/"; valid iff _is_valid_stem
    name = None
    slash_idx = rest.rfind("/")
    candidate = rest[slash_idx + 1 :]
    if _is_valid_stem(candidate):
        name = candidate
        rest = rest[: slash_idx + 1]

    # dir: whatever remains; Path() strips the trailing slash
    dir = _parse_dir(rest) if rest else None

    return dir, name, ext


def parse_save(args: list[str]) -> SaveSpec:
    components: dict[str, Path | str] = {}
    seen_fragment = False

    def set_component(key: str, value: Path | str):
        if key in components:
            raise argparse.ArgumentTypeError(f"Expected {key} to be specified at most once; got '{components[key]}' and '{value}'")
        components[key] = value

    for arg in args:
        key, sep, value = arg.partition("=")

        # An arg is a key=value attempt iff an identifier precedes the first "=".
        # Anything else (out/fig=x, a-b=c) is a bare fragment, which is how stems
        # containing "=" — as derived stems do — get through without a name= key.
        if sep and parse_util.is_identifier(key):
            parse_util.parse_value(key, "save key", _KEYS)

            if key == "dir":
                if not value:
                    raise argparse.ArgumentTypeError("Expected dir to be a nonempty path; got ''")
                set_component("dir", _parse_dir(value))
            elif key == "name":
                if "/" in value or not _is_valid_stem(value):
                    raise argparse.ArgumentTypeError(f"Expected name to be a stem with no '/' and at least one non-'.' character; got '{value}'")
                set_component("name", value)
            elif key == "format":
                if not value or "." in value or "/" in value:
                    raise argparse.ArgumentTypeError(f"Expected format to be a nonempty extension with no '.' or '/'; got '{value}'")
                set_component("format", value)
            else:
                raise AssertionError(key)
        else:
            if seen_fragment:
                raise argparse.ArgumentTypeError(f"Expected at most one path fragment; got a second one: '{arg}'")
            seen_fragment = True

            dir, name, ext = _split_fragment(arg)
            if dir is not None:
                set_component("dir", dir)
            if name is not None:
                set_component("name", name)
            if ext is not None:
                set_component("format", ext)

    return SaveSpec(**components)
