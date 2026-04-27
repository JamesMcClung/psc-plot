import pathlib
import typing
import warnings
from collections import defaultdict

import dask.dataframe as dd
import h5py
import numpy as np

from lib.config import CONFIG
from lib.data.data_with_attrs import LazyList, ListMetadata
from lib.data.loader_registry import loader
from lib.data.source import DataSource
from lib.file_util import get_available_steps
from lib.latex import Latex
from lib.species import SpeciesInfo
from lib.var_info_registry import lookup

PRT_PARTICLES_KEY = "particles/p0/1d"
type SpeciesIdx = int
type Charge = float
type Mass = float


def _get_path_at_step(prefix: str, step: int) -> pathlib.Path:
    return CONFIG.data_dir / f"{prefix}.{step:09}.h5"


def _load_attrs_at_step(prefix: str, step: int) -> dict[str, typing.Any]:
    data_path = _get_path_at_step(prefix, step)
    attrs = {}
    with h5py.File(data_path) as file:
        if "time" not in file.keys():
            raise Exception("Particle data missing 'time' is no longer supported")

        attrs["time"] = file["time"][()]
        attrs["corner"] = file["corner"][:]
        attrs["length"] = file["length"][:]
        attrs["gdims"] = file["gdims"][:]

    return attrs


def _find_first_populated_cell(idx_begin_s: np.ndarray, idx_end_s: np.ndarray) -> int | None:
    """Given idx_begin/idx_end slices for one species (shape (z,y,x)), return the
    first particle row-index where that species has >=1 particle, or None."""
    mask = idx_begin_s < idx_end_s
    if not mask.any():
        return None
    return int(idx_begin_s[mask].min())


def _read_species_qm(prefix: str, step: int, missing: set[SpeciesIdx]) -> dict[SpeciesIdx, tuple[Charge, Mass]]:
    """Open one step and return {species_index: (q, m)} for any species with particles in that step.
    Only populates entries for species-indices in `missing`; others are left untouched."""
    with h5py.File(_get_path_at_step(prefix, step)) as f:
        idx_begin = f["particles/idx_begin"][...]
        idx_end = f["particles/idx_end"][...]
        particles = f[PRT_PARTICLES_KEY]
        found = {}
        for s in list(missing):
            row = _find_first_populated_cell(idx_begin[s], idx_end[s])
            if row is None:
                continue
            p = particles[row]
            found[s] = (float(p["q"]), float(p["m"]))
    return found


def _discover_species_qm(prefix: str, steps: list[int]) -> dict[SpeciesIdx, tuple[Charge, Mass]]:
    """For each species index in [0, n_species), find a step where it has particles
    and read its (q, m). Tries step 0 first, then the last step, then bisects the
    remaining range. Raises if any species never appears."""
    with h5py.File(_get_path_at_step(prefix, steps[0])) as f:
        n_species = f["particles/idx_begin"].shape[0]
    qm: dict[SpeciesIdx, tuple[Charge, Mass]] = {}
    missing = set(range(n_species))

    probed: set[int] = set()
    to_probe: list[int] = [steps[0]]
    if len(steps) > 1:
        to_probe.append(steps[-1])

    while missing and to_probe:
        step = to_probe.pop(0)
        if step in probed:
            continue
        probed.add(step)
        found = _read_species_qm(prefix, step, missing)
        qm.update(found)
        missing -= set(found.keys())
        if not missing:
            break
        probed_sorted = sorted(probed)
        for a, b in zip(probed_sorted, probed_sorted[1:]):
            candidates = [s for s in steps if a < s < b and s not in probed]
            if not candidates:
                continue
            mid = candidates[len(candidates) // 2]
            if mid not in to_probe:
                to_probe.append(mid)

    if missing:
        raise ValueError(f"could not locate particles for species indices {sorted(missing)} in any step")
    return qm


def _build_species_dict(qm: dict[SpeciesIdx, tuple[Charge, Mass]]) -> dict[str, SpeciesInfo]:
    """Turn {species_index: (q, m)} into {species_key: SpeciesInfo}.

    Dedupes by (q, m) first (with a warning on collision), then groups unique
    (q, m) pairs by sign(q). Singletons in a sign-group get keys 'e' / 'i';
    multi-member groups get charge- and/or mass-suffixed keys like 'i+'/'i++'
    (different charges) or 'i25' / 'i100' (same charge, different masses).
    """
    qm_to_indices: dict[tuple[Charge, Mass], list[SpeciesIdx]] = defaultdict(list)
    for s, key in qm.items():
        qm_to_indices[key].append(s)
    for (q, m), indices in qm_to_indices.items():
        if len(indices) > 1:
            warnings.warn(
                f"merging species with identical (q, m)=({q}, {m}): indices {sorted(indices)} collapsed",
                UserWarning,
                stacklevel=3,
            )
    unique_qm: list[tuple[Charge, Mass]] = list(qm_to_indices.keys())

    sign_groups: dict[SpeciesIdx, list[tuple[Charge, Mass]]] = defaultdict(list)
    for q, m in unique_qm:
        sign_groups[1 if q > 0 else -1].append((q, m))

    result: dict[str, SpeciesInfo] = {}
    for sign, qms in sign_groups.items():
        base, subject = ("i", "Ions") if sign > 0 else ("e", "Electrons")

        masses_are_unique = len(set(qm[1] for qm in qms)) == len(qms)
        charges_are_unique = len(set(qm[0] for qm in qms)) == len(qms)

        if charges_are_unique and masses_are_unique:
            q, m = qms[0]
            key = base
            display = Latex(rf"\text{{{subject}}}")
            result[key] = SpeciesInfo(species_key=key, display=display, q=q, m=m)
        elif charges_are_unique:
            q_char = "+" if sign > 0 else "-"
            for q, m in qms:
                n_signs = int(abs(q))
                key = base + q_char * n_signs
                display = Latex(rf"\text{{{subject}}}^{{{n_signs if n_signs > 1 else ""}{q_char}}}")
                result[key] = SpeciesInfo(species_key=key, display=display, q=q, m=m)
        elif masses_are_unique:
            for q, m in qms:
                key = f"{base}{m:g}"
                display = Latex(rf"\text{{{subject}}}_{{{m:g}}}")
                result[key] = SpeciesInfo(species_key=key, display=display, q=q, m=m)
        else:
            q_char = "+" if sign > 0 else "-"
            for q, m in qms:
                n_signs = int(abs(q))
                key = f"{base}{q_char * n_signs}{m:g}"
                display = Latex(rf"\text{{{subject}}}^{{{n_signs if n_signs > 1 else ""}{q_char}}}_{{{m:g}}}")
                result[key] = SpeciesInfo(species_key=key, display=display, q=q, m=m)
    return result


@loader("prt")
class ParticleLoaderH5(DataSource):
    def __init__(self, prefix: str, active_key: str | None):
        self.prefix = prefix
        self.active_key = active_key
        self.steps = get_available_steps(f"{prefix}.", ".h5")

    def get_data(self) -> LazyList:
        species_dict = _build_species_dict(_discover_species_qm(self.prefix, self.steps))

        attrss = [_load_attrs_at_step(self.prefix, step) for step in self.steps]
        times = np.array([attrs["time"] for attrs in attrss])

        data_paths = [_get_path_at_step(self.prefix, step) for step in self.steps]
        dfs_of_steps = []
        for time, data_path in zip(times, data_paths):
            df_of_step: dd.DataFrame = dd.read_hdf(data_path, key=PRT_PARTICLES_KEY, chunksize=CONFIG.dask_chunk_size, lock=True)
            df_of_step = df_of_step.assign(t=time)
            dfs_of_steps.append(df_of_step)

        df: dd.DataFrame = dd.concat(dfs_of_steps)

        corners = np.array(attrss[0]["corner"])
        lengths = np.array(attrss[0]["length"])
        gdims = np.array(attrss[0]["gdims"])
        coordss = {dim: np.linspace(corner, corner + length, ncells, endpoint=False) for dim, corner, length, ncells in zip(("x", "y", "z"), corners, lengths, gdims)}
        coordss["t"] = times

        metadata = ListMetadata(
            weight_key="w",
            coordss=coordss,
            species=species_dict,
        )

        df_with_metadata = LazyList(df, metadata)

        var_infos = {key: lookup(self.prefix, key) for key in df_with_metadata.dims}
        return df_with_metadata.assign_metadata(
            name_fragments=self._get_name_fragments(),
            active_key=self.active_key,
            var_infos=var_infos,
            subject=Latex(r"\text{Particles}"),
        )

    def _get_name_fragments(self) -> list[str]:
        fragments = [self.prefix]
        if self.active_key is not None:
            fragments.append(self.active_key)
        return fragments
