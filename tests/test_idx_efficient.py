"""Structural perf test: --idx t=<n> should read bulk array data from at most
one file. See docs/superpowers/specs/2026-05-14-efficient-time-indexing-design.md.

The fixture monkeypatches adios2py.file.File._read (the single bulk-read entry
point used by both field and particle pipelines) and records (filename, var)
for every call. Tests assert that, after running a pipeline with --idx t=-1,
the active variable was read from exactly one .bp file.
"""

from __future__ import annotations

import pytest

from lib.data.compile import compile_args
from lib.parsing.parse import get_parsed_args


@pytest.fixture
def files_and_vars(monkeypatch: pytest.MonkeyPatch):
    """Records every adios2 bulk read as (filename, var_name)."""
    from adios2py.file import File

    files_and_vars: list[tuple[str, str]] = []
    original_read = File._read

    def counting_read(self: File, var_name: str, index):
        files_and_vars.append((str(self._filename), var_name))
        return original_read(self, var_name, index)

    monkeypatch.setattr(File, "_read", counting_read)
    return files_and_vars


def test_field_idx_t(files_and_vars):
    args = get_parsed_args("pfd ex_ec --idx t=-1 -v y z time= --compute".split())
    compile_args(args).pull()._initialize()

    # 'jeh' is the raw adios2 variable that holds all pfd components.
    files_read = {f for f, var in files_and_vars if var == "jeh"}
    assert len(files_read) == 1, f"--idx t=-1 read 'jeh' from {len(files_read)} files; expected 1. files: {sorted(files_read)}"


def test_particle_bp_idx_t(files_and_vars):
    args = get_parsed_args("prt.e --idx t=-1 -v y z time= --compute".split())
    compile_args(args).pull()._initialize()

    # Particle position columns; if any of these is read from >1 file, the
    # loader is scanning steps it shouldn't.
    position_vars = {"y", "z"}
    files_read = {f for f, var in files_and_vars if var in position_vars}
    assert len(files_read) == 1, f"--idx t=-1 read particle columns from {len(files_read)} files; expected 1. files: {sorted(files_read)}"


def test_field_pos_t(files_and_vars):
    # t=999 is past max(t) in test-2d, so "nearest" resolves to the last file.
    args = get_parsed_args("pfd ex_ec --pos t=999 -v y z time= --compute".split())
    compile_args(args).pull()._initialize()

    files_read = {f for f, var in files_and_vars if var == "jeh"}
    assert len(files_read) == 1, f"--pos t=999 read 'jeh' from {len(files_read)} files; expected 1. files: {sorted(files_read)}"


def test_particle_bp_pos_t(files_and_vars):
    args = get_parsed_args("prt.e --pos t=999 -v y z time= --compute".split())
    compile_args(args).pull()._initialize()

    position_vars = {"y", "z"}
    files_read = {f for f, var in files_and_vars if var in position_vars}
    assert len(files_read) == 1, f"--pos t=999 read particle columns from {len(files_read)} files; expected 1. files: {sorted(files_read)}"
