import importlib.metadata
import os
import platform
import socket
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import psutil

from lib.config import CONFIG_KEYS, ConfigValue, PscPlotConfig, config_file_path_from_env
from lib.profiling.units import format_bytes, format_optional

_JOB_VARS = {
    "SGE": ("JOB_ID", "NSLOTS", "PE", "QUEUE"),
    "PBS": ("PBS_JOBID", "NCPUS", "PBS_QUEUE"),
    "Slurm": ("SLURM_JOB_ID", "SLURM_CPUS_PER_TASK", "SLURM_NTASKS", "SLURM_JOB_NODELIST"),
}
_HOSTFILE_VARS = ("PE_HOSTFILE", "PBS_NODEFILE")
_THREAD_VARS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")
_VERSIONED_DISTRIBUTIONS = ("numpy", "xarray", "dask", "distributed", "adios2", "xarray-adios2", "pscpy", "h5py", "matplotlib", "psutil")


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def cgroup_cpu_quota(cgroup_root: Path = Path("/sys/fs/cgroup")) -> float | None:
    """The cgroup's CPU limit in cores (v2 `cpu.max`, then v1 CFS quota), or None when unlimited or unknown."""
    if (cpu_max := _read(cgroup_root / "cpu.max")) is not None:
        quota, _, period = cpu_max.partition(" ")
        return None if quota == "max" else int(quota) / int(period)
    quota = _read(cgroup_root / "cpu" / "cpu.cfs_quota_us")
    period = _read(cgroup_root / "cpu" / "cpu.cfs_period_us")
    if quota is None or period is None or int(quota) <= 0:
        return None
    return int(quota) / int(period)


def _cgroup_cpuset(cgroup_root: Path = Path("/sys/fs/cgroup")) -> str | None:
    return _read(cgroup_root / "cpuset.cpus.effective") or _read(cgroup_root / "cpuset" / "cpuset.cpus")


def _detect_job_scheduler(environ: Mapping[str, str]) -> str | None:
    if "SLURM_JOB_ID" in environ:
        return "Slurm"
    if "PBS_JOBID" in environ:
        return "PBS"
    if "JOB_ID" in environ and ("SGE_ROOT" in environ or "NSLOTS" in environ):
        return "SGE"
    return None


def _hosts(environ: Mapping[str, str]) -> list[str]:
    """Distinct hostnames, in order, from the job's hostfile; a single process can only use its own node's slots."""
    hosts: list[str] = []
    for var in _HOSTFILE_VARS:
        if var in environ and (text := _read(Path(environ[var]))) is not None:
            for line in text.splitlines():
                if (fields := line.split()) and fields[0] not in hosts:
                    hosts.append(fields[0])
    return hosts


def _version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _format_config_value(value: ConfigValue) -> str:
    if value is None:
        return "null"
    if isinstance(value, list):
        return "[" + ", ".join(value) + "]"
    return value


@dataclass(frozen=True)
class EnvironmentReport:
    host: str
    platform: str
    python_version: str
    gil_enabled: bool
    cpu_logical: int | None
    cpu_physical: int | None
    cpu_affinity: int | None
    cgroup_cpu_quota: float | None
    cgroup_cpuset: str | None
    mem_total: int
    mem_available: int
    job_scheduler: str | None
    job_vars: dict[str, str]
    hosts: list[str]
    thread_vars: dict[str, str]
    versions: dict[str, str | None]
    config_path: Path
    env_overrides: list[str]
    config_values: dict[str, ConfigValue]

    @classmethod
    def collect(cls, config: PscPlotConfig, environ: Mapping[str, str] = os.environ) -> "EnvironmentReport":
        job_scheduler = _detect_job_scheduler(environ)
        job_var_names = _JOB_VARS.get(job_scheduler, ())
        memory = psutil.virtual_memory()
        return cls(
            host=socket.gethostname(),
            platform=platform.platform(),
            python_version=sys.version.split()[0],
            gil_enabled=getattr(sys, "_is_gil_enabled", lambda: True)(),
            cpu_logical=os.cpu_count(),
            cpu_physical=psutil.cpu_count(logical=False),
            cpu_affinity=len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
            cgroup_cpu_quota=cgroup_cpu_quota(),
            cgroup_cpuset=_cgroup_cpuset(),
            mem_total=memory.total,
            mem_available=memory.available,
            job_scheduler=job_scheduler,
            job_vars={var: environ[var] for var in job_var_names if var in environ},
            hosts=_hosts(environ),
            thread_vars={var: environ[var] for var in _THREAD_VARS if var in environ},
            versions={distribution: _version(distribution) for distribution in _VERSIONED_DISTRIBUTIONS},
            config_path=config_file_path_from_env(environ),
            env_overrides=[key for key in CONFIG_KEYS if key in environ],
            config_values=config.to_mapping(),
        )

    def format_text(self) -> str:
        gil = "GIL enabled" if self.gil_enabled else "GIL disabled"
        quota = "none" if self.cgroup_cpu_quota is None else f"{self.cgroup_cpu_quota:g} cores"
        cpuset = "" if self.cgroup_cpuset is None else f" · cpuset {self.cgroup_cpuset}"
        if self.job_scheduler is None:
            job = "none detected"
        else:
            job = "  ".join([self.job_scheduler, *(f"{var}={value}" for var, value in self.job_vars.items())])
        if self.hosts:
            job += f"  hosts=[{', '.join(self.hosts)}]"
        overrides = ", ".join(self.env_overrides) or "none"
        lines = [
            "== environment ==",
            f"host     {self.host} · {self.platform} · python {self.python_version} ({gil})",
            f"cpus     {format_optional(self.cpu_logical)} logical · {format_optional(self.cpu_physical)} physical · {format_optional(self.cpu_affinity)} in affinity mask · cgroup quota {quota}{cpuset}",
            f"memory   {format_bytes(self.mem_total)} total · {format_bytes(self.mem_available)} available",
            f"job      {job}",
        ]
        if self.thread_vars:
            lines.append("threads  " + "  ".join(f"{var}={value}" for var, value in self.thread_vars.items()))
        lines.append(f"config   {self.config_path}   (env overrides: {overrides})")
        lines.extend(f"  {key}: {_format_config_value(value)}" for key, value in self.config_values.items())
        lines.append("versions " + " · ".join(f"{name} {format_optional(version)}" for name, version in self.versions.items()))
        return "\n".join(lines)
