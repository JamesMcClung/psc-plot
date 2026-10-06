import math
from dataclasses import replace

from conftest import CONFIG_2D

from lib.config import CONFIG_KEYS
from lib.profiling.environment import EnvironmentReport, cgroup_cpu_quota, cgroup_cpuset


def test_detects_sge_job_and_hosts(tmp_path):
    hostfile = tmp_path / "pe_hostfile"
    hostfile.write_text("compute-12 16 all.q@compute-12 UNDEFINED\ncompute-13 16 all.q@compute-13 UNDEFINED\ncompute-12 4 short.q@compute-12 UNDEFINED\n")
    environ = {"JOB_ID": "1234", "SGE_ROOT": "/opt/sge", "NSLOTS": "32", "PE": "mthread", "PE_HOSTFILE": str(hostfile)}
    report = EnvironmentReport.collect(CONFIG_2D, environ=environ)
    assert report.job_scheduler == "SGE"
    assert report.job_vars == {"JOB_ID": "1234", "NSLOTS": "32", "PE": "mthread"}
    assert report.hosts == ["compute-12", "compute-13"]


def test_detects_pbs_and_slurm():
    assert EnvironmentReport.collect(CONFIG_2D, environ={"PBS_JOBID": "9.pbs", "NCPUS": "28"}).job_scheduler == "PBS"
    assert EnvironmentReport.collect(CONFIG_2D, environ={"SLURM_JOB_ID": "7"}).job_scheduler == "Slurm"
    assert EnvironmentReport.collect(CONFIG_2D, environ={}).job_scheduler is None


def test_config_provenance(tmp_path):
    environ = {"PSC_PLOT_CONFIG_PATH": str(tmp_path / "config.yml"), "PSC_PLOT_DASK_NUM_WORKERS": "32", "OMP_NUM_THREADS": "1"}
    report = EnvironmentReport.collect(CONFIG_2D, environ=environ)
    assert report.config_path == tmp_path / "config.yml"
    assert report.env_overrides == ["PSC_PLOT_DASK_NUM_WORKERS"]
    assert report.config_values == CONFIG_2D.to_mapping()
    assert report.thread_vars == {"OMP_NUM_THREADS": "1"}


def test_format_text_lists_every_config_key():
    text = EnvironmentReport.collect(CONFIG_2D, environ={}).format_text()
    assert text.startswith("== environment ==")
    for key in CONFIG_KEYS:
        assert f"  {key}: " in text


def test_format_text_with_missing_values():
    report = EnvironmentReport.collect(CONFIG_2D, environ={})
    report = replace(report, cpu_physical=None, cpu_affinity=None, cgroup_cpu_quota=None, cgroup_cpuset=None, versions={"adios2": None})
    text = report.format_text()
    assert "n/a physical" in text
    assert "n/a in affinity mask" in text
    assert "adios2 n/a" in text
    assert "job      none detected" in text


def _cgroup_fs(tmp_path, proc_cgroup: str, files: dict[str, str]):
    """A fake cgroup mount at tmp_path/cgroup and /proc/self/cgroup at tmp_path/proc_cgroup."""
    root = tmp_path / "cgroup"
    root.mkdir(parents=True)
    for relative, text in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text)
    (tmp_path / "proc_cgroup").write_text(proc_cgroup)
    return root, tmp_path / "proc_cgroup"


def test_cgroup_v2_quota_is_tightest_ancestor(tmp_path):
    root, proc = _cgroup_fs(tmp_path, "0::/job/step\n", {"job/cpu.max": "200000 100000\n", "job/step/cpu.max": "max 100000\n"})
    assert cgroup_cpu_quota(root, proc) == 2.0


def test_cgroup_v2_unlimited(tmp_path):
    root, proc = _cgroup_fs(tmp_path, "0::/job\n", {"job/cpu.max": "max 100000\n"})
    assert cgroup_cpu_quota(root, proc) == math.inf


def test_cgroup_v1_quota(tmp_path):
    root, proc = _cgroup_fs(tmp_path, "5:cpuset:/sge/1234\n4:cpu,cpuacct:/sge/1234\n", {"cpu/sge/1234/cpu.cfs_quota_us": "400000\n", "cpu/sge/1234/cpu.cfs_period_us": "100000\n"})
    assert cgroup_cpu_quota(root, proc) == 4.0
    (root / "cpu/sge/1234/cpu.cfs_quota_us").write_text("-1\n")
    assert cgroup_cpu_quota(root, proc) == math.inf


def test_cgroup_unknown(tmp_path):
    root, proc = _cgroup_fs(tmp_path, "0::/job\n", {})
    assert cgroup_cpu_quota(root, proc) is None
    assert cgroup_cpu_quota(root, tmp_path / "no_such_file") is None


def test_cgroup_cpuset_reads_own_cgroup(tmp_path):
    root, proc = _cgroup_fs(tmp_path, "0::/job\n", {"cpuset.cpus.effective": "0-63\n", "job/cpuset.cpus.effective": "0-31\n"})
    assert cgroup_cpuset(root, proc) == "0-31"
    root, proc = _cgroup_fs(tmp_path / "v1", "3:cpuset:/sge/1234\n", {"cpuset/sge/1234/cpuset.cpus": "8-15\n"})
    assert cgroup_cpuset(root, proc) == "8-15"


def test_format_text_quota():
    report = EnvironmentReport.collect(CONFIG_2D, environ={})
    assert "cgroup quota n/a" in replace(report, cgroup_cpu_quota=None).format_text()
    assert "cgroup quota none" in replace(report, cgroup_cpu_quota=math.inf).format_text()
    assert "cgroup quota 2 cores" in replace(report, cgroup_cpu_quota=2.0).format_text()
