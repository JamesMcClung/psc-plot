import math
from dataclasses import dataclass

from lib.profiling.environment import EnvironmentReport

# the variable holding a job's slot count, per job scheduler
_SLOT_VARS = {"SGE": "NSLOTS", "PBS": "NCPUS", "Slurm": "SLURM_CPUS_PER_TASK"}


@dataclass(frozen=True)
class WorkerCount:
    """How many dask workers this machine and job support, and why."""

    value: int
    slot_var: str | None  # the job's slot variable, when it achieves the minimum
    basis: str

    @classmethod
    def from_environment(cls, environment: EnvironmentReport) -> "WorkerCount":
        limits: list[tuple[str, int]] = []
        slot_var = _SLOT_VARS.get(environment.job_scheduler)
        slots = environment.job_vars.get(slot_var, "") if slot_var else ""
        if slots.isdigit():
            limits.append((slot_var, int(slots)))
        if environment.cpu_affinity is not None:
            limits.append(("affinity", environment.cpu_affinity))
        if environment.cgroup_cpu_quota is not None and environment.cgroup_cpu_quota != math.inf:
            limits.append(("cgroup quota", max(1, math.floor(environment.cgroup_cpu_quota))))
        if environment.cpu_physical is not None:
            limits.append(("physical", environment.cpu_physical))

        if not limits:
            if environment.cpu_logical is not None:
                return cls(environment.cpu_logical, None, f"os.cpu_count()={environment.cpu_logical}")
            return cls(1, None, "no CPU limits known")

        value = min(limit for _, limit in limits)
        terms = ", ".join(f"{name}={limit}" for name, limit in limits)
        basis = f"min of {terms}" if len(limits) > 1 else terms
        binding_slot_var = slot_var if (slot_var, value) in limits else None
        return cls(value, binding_slot_var, basis)

    def yaml_value(self) -> str:
        """The config file value: the slot variable when it sets the count, so the file is reusable across jobs."""
        return f"${self.slot_var}" if self.slot_var else str(self.value)

    def comment(self) -> str:
        return f"= {self.value} here; {self.basis}" if self.slot_var else self.basis
