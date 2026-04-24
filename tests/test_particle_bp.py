"""Tests for ParticleLoaderBp registration and loading."""
from lib.config import CONFIG
from lib.parsing.parse import _get_parser
from synthetic_particles import write_steps_bp


def test_dynamic_prefix_registration(tmp_path, monkeypatch):
    """Parser's prefix choices should include prt.<species_key> for every
    prt.*.bp species found in CONFIG.data_dir."""
    write_steps_bp(
        tmp_path,
        steps=[0, 1],
        times=[0.0, 1.0],
        species=[("e", -1.0, 1.0, 10), ("i25", 1.0, 25.0, 10)],
    )
    monkeypatch.setattr(CONFIG, "data_dir", tmp_path)

    parser = _get_parser()
    prefix_action = next(a for a in parser._actions if a.dest == "prefix")
    choices = set(prefix_action.choices)
    assert "prt.e" in choices
    assert "prt.i25" in choices
