"""Tests for `--concat`, which appends another prepath's particle list to the active one."""

from __future__ import annotations

import numpy as np
import pytest
from conftest import CONFIG_2D

from lib.data.data_with_attrs import List
from lib.parsing.parse import parse_args
from lib.run.compile import compile_plot_pipeline


def _pull_active(argv: str):
    return compile_plot_pipeline(parse_args(argv.split()), CONFIG_2D).run_world().require_active_data()


def test_concat_rows_and_metadata():
    ions = _pull_active("prt.i -v y z")
    electrons = _pull_active("prt.e -v y z")
    data = _pull_active("prt.i --concat prt.e -v y z")

    assert isinstance(data, List)
    assert len(data.data) == len(ions.data) + len(electrons.data)
    assert list(data.data.columns) == list(ions.data.columns)
    assert set(data.metadata.species) == {"i", "e"}
    assert data.metadata.prepath == "prt.i"


def test_concat_subject_joins_distinct_subjects():
    data = _pull_active("prt.i --concat prt.e -v y z")
    assert data.metadata.subject.latex == r"\text{Ions}\text{ and }\text{Electrons}"
    assert data.metadata.subject.plain == "Ions and Electrons"


def test_concat_subject_kept_when_equal():
    data = _pull_active("prt.i --concat prt.i -v y z")
    assert data.metadata.subject.latex == r"\text{Ions}"


def test_concat_keeps_partitions_laid_out_along_t():
    """Each step's partitions must hold only that step's rows, from both lists."""
    data = _pull_active("prt.i --concat prt.e -v y z")
    md = data.metadata
    assert md.partition_dim == "t"
    assert len(md.partition_ranges) == len(md.coordss["t"])
    assert md.partition_ranges[-1][1] == data.data.npartitions

    for step, (start, end) in enumerate(md.partition_ranges):
        times = data.data.partitions[start:end]["t"].compute().unique()
        assert list(times) == [md.coordss["t"][step]]


def test_idx_t_after_concat_selects_both_lists():
    ions = _pull_active("prt.i -i t=3 -v y z")
    electrons = _pull_active("prt.e -i t=3 -v y z")
    data = _pull_active("prt.i --concat prt.e -i t=3 -v y z")
    assert len(data.data) == len(ions.data) + len(electrons.data)


def test_bin_after_concat_with_self_doubles():
    single = _pull_active("prt.i --bin y=8 py=16 -v y py")
    double = _pull_active("prt.i --concat prt.i --bin y=8 py=16 -v y py")
    np.testing.assert_allclose(double.require_active_subdata().values, 2 * single.require_active_subdata().values)
    # an unchanged subject still gets the species subscript
    assert double.active_info.display.latex.endswith(r"_\text{i}")


def test_concat_rejects_mismatched_coords():
    with pytest.raises(ValueError, match="coordinates"):
        _pull_active("prt.i -i t=0:3 --concat prt.e -v y z")


def test_concat_rejects_field_data():
    with pytest.raises(ValueError, match="list"):
        _pull_active("pfd ex_ec --concat prt.e")


def test_concat_name_fragment():
    pipeline = compile_plot_pipeline(parse_args("prt.i --concat prt.e -v y z".split()), CONFIG_2D)
    assert "concat_prt.e" in pipeline.get_save_file_stem()
