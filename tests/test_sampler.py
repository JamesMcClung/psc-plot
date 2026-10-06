import mmap
import subprocess
import sys

from lib.profiling.sampler import ProcessTreeSampler


def _busy_child(cpu_seconds: float) -> subprocess.Popen:
    code = f"import time\nend = time.process_time() + {cpu_seconds}\nwhile time.process_time() < end:\n    pass\n"
    return subprocess.Popen([sys.executable, "-c", code])


def _resident_block(size: int) -> mmap.mmap:
    """Map and touch `size` bytes; `close()` unmaps them. Bypasses malloc, whose freed memory may stay resident (e.g. macOS 15)."""
    block = mmap.mmap(-1, size)
    for offset in range(0, size, mmap.PAGESIZE):
        block[offset] = 1
    return block


def test_counts_cpu_of_exited_child():
    with ProcessTreeSampler(interval=0.05) as sampler:
        window = sampler.open_window()
        _busy_child(0.5).wait()
        cpu, _ = sampler.close_window(window)
    assert cpu >= 0.3


def test_counts_child_started_before_window():
    child = _busy_child(1.0)
    with ProcessTreeSampler(interval=0.05) as sampler:
        window = sampler.open_window()
        child.wait()
        cpu, _ = sampler.close_window(window)
    assert cpu >= 0.5


def test_peak_rss_survives_free():
    with ProcessTreeSampler(interval=0.05) as sampler:
        window = sampler.open_window()
        _, rss_before = sampler.sample()
        block = _resident_block(200 * 2**20)
        sampler.sample()
        block.close()
        _, peak = sampler.close_window(window)
    assert peak >= rss_before + 150 * 2**20


def test_windows_track_peaks_independently():
    with ProcessTreeSampler(interval=0.05) as sampler:
        outer = sampler.open_window()
        block = _resident_block(200 * 2**20)
        sampler.sample()
        block.close()
        inner = sampler.open_window()
        _, inner_peak = sampler.close_window(inner)
        _, outer_peak = sampler.close_window(outer)
    assert outer_peak >= inner_peak + 150 * 2**20
