from dataclasses import replace

from conftest import CONFIG_2D

from lib.config import CONFIG_KEYS
from lib.profiling.environment import EnvironmentReport, cgroup_cpu_quota


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


def test_cgroup_v2_quota(tmp_path):
    (tmp_path / "cpu.max").write_text("200000 100000\n")
    assert cgroup_cpu_quota(tmp_path) == 2.0
    (tmp_path / "cpu.max").write_text("max 100000\n")
    assert cgroup_cpu_quota(tmp_path) is None


def test_cgroup_v1_quota(tmp_path):
    (tmp_path / "cpu").mkdir()
    (tmp_path / "cpu" / "cpu.cfs_quota_us").write_text("400000\n")
    (tmp_path / "cpu" / "cpu.cfs_period_us").write_text("100000\n")
    assert cgroup_cpu_quota(tmp_path) == 4.0
    (tmp_path / "cpu" / "cpu.cfs_quota_us").write_text("-1\n")
    assert cgroup_cpu_quota(tmp_path) is None


def test_no_cgroup(tmp_path):
    assert cgroup_cpu_quota(tmp_path) is None
