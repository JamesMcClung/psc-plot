import math
from dataclasses import replace

from conftest import CONFIG_2D

from lib.profiling.environment import EnvironmentReport
from lib.profiling.worker_count import WorkerCount


def _report(environ: dict[str, str], **fields) -> EnvironmentReport:
    defaults = {"cpu_logical": None, "cpu_physical": None, "cpu_affinity": None, "cgroup_cpu_quota": None}
    return replace(EnvironmentReport.collect(CONFIG_2D, environ=environ), **(defaults | fields))


def test_job_slots_achieve_the_minimum():
    workers = WorkerCount.from_environment(_report({"PBS_JOBID": "9.pbs", "NCPUS": "28"}, cpu_affinity=56, cpu_physical=28, cgroup_cpu_quota=math.inf))
    assert workers == WorkerCount(28, "NCPUS", "min of NCPUS=28, affinity=56, physical=28")
    assert workers.yaml_value() == "$NCPUS"
    assert workers.comment() == "= 28 here; min of NCPUS=28, affinity=56, physical=28"


def test_slots_spanning_nodes_are_capped_at_this_nodes_cores():
    workers = WorkerCount.from_environment(_report({"JOB_ID": "1", "SGE_ROOT": "/sge", "NSLOTS": "64"}, cpu_affinity=64, cpu_physical=32))
    assert workers == WorkerCount(32, None, "min of NSLOTS=64, affinity=64, physical=32")
    assert workers.yaml_value() == "32"
    assert workers.comment() == "min of NSLOTS=64, affinity=64, physical=32"


def test_cgroup_quota_is_floored():
    workers = WorkerCount.from_environment(_report({}, cpu_affinity=8, cpu_physical=4, cgroup_cpu_quota=2.5))
    assert workers == WorkerCount(2, None, "min of affinity=8, cgroup quota=2, physical=4")


def test_fractional_quota_below_one_still_gives_a_worker():
    assert WorkerCount.from_environment(_report({}, cgroup_cpu_quota=0.5)).value == 1


def test_single_limit():
    assert WorkerCount.from_environment(_report({}, cpu_physical=4)) == WorkerCount(4, None, "physical=4")


def test_non_integer_slot_var_is_ignored():
    workers = WorkerCount.from_environment(_report({"SLURM_JOB_ID": "7", "SLURM_CPUS_PER_TASK": "lots"}, cpu_physical=4))
    assert workers == WorkerCount(4, None, "physical=4")


def test_nothing_known_falls_back_to_logical_cpus_then_one():
    assert WorkerCount.from_environment(_report({}, cpu_logical=6)) == WorkerCount(6, None, "os.cpu_count()=6")
    assert WorkerCount.from_environment(_report({})) == WorkerCount(1, None, "no CPU limits known")
