"""Structural perf test: --idx t=<n> should read bulk array data from at most
one file. See docs/superpowers/specs/2026-05-14-efficient-time-indexing-design.md.

The fixture monkeypatches adios2py.file.File._read (the single bulk-read entry
point used by both field and particle pipelines) and records (filename, var)
for every call. Tests assert that, after running a pipeline with --idx t=-1,
the active variable was read from exactly one .bp file.
"""

from __future__ import annotations

import pytest

from lib.parsing.parse import get_parsed_args


@pytest.fixture
def bulk_read_counter(monkeypatch):
    """Records every adios2 bulk read as (filename, var_name)."""
    from adios2py.file import File

    calls: list[tuple[str, str]] = []
    original = File._read

    def counting_read(self, name, index):
        calls.append((str(self._filename), name))
        return original(self, name, index)

    monkeypatch.setattr(File, "_read", counting_read)
    return calls


def test_field_idx_t_last_reads_only_indexed_file(bulk_read_counter):
    args = get_parsed_args("pfd ex_ec --idx t=-1 -v y z time= --compute".split())
    args.get_animation()._initialize()

    # 'jeh' is the raw adios2 variable that holds all pfd components.
    files_read = {f for f, var in bulk_read_counter if var == "jeh"}
    assert len(files_read) == 1, f"--idx t=-1 read 'jeh' from {len(files_read)} files; expected 1. files: {sorted(files_read)}"


@pytest.mark.xfail(reason="dd.concat scans all partitions; fix deferred — see docs/superpowers/specs/2026-05-14-efficient-time-indexing-design.md")
def test_particle_idx_t_last_reads_only_indexed_file(bulk_read_counter):
    args = get_parsed_args("prt.e --idx t=-1 -v y z time= --compute".split())
    args.get_animation()._initialize()

    # Particle position columns; if any of these is read from >1 file, the
    # loader is scanning steps it shouldn't.
    position_vars = {"x", "y", "z", "w"}
    files_read = {f for f, var in bulk_read_counter if var in position_vars}
    assert len(files_read) == 1, f"--idx t=-1 read particle columns from {len(files_read)} files; expected 1. files: {sorted(files_read)}"
