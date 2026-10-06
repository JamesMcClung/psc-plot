import threading
from dataclasses import dataclass

import psutil


@dataclass
class SampleWindow:
    cpu_start: float
    peak_rss: int


class ProcessTreeSampler:
    """Samples CPU time and RSS summed over this process and all its descendants (e.g. dask worker processes).

    A background thread samples every `interval` seconds, so peaks between stage boundaries are caught. A descendant's CPU time is remembered after it exits.
    """

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self._root = psutil.Process()
        self._cpu_by_pid: dict[int, float] = {}
        self._windows: list[SampleWindow] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def __enter__(self):
        self.sample()
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()

    def _loop(self):
        while not self._stop.wait(self.interval):
            self.sample()

    def sample(self) -> tuple[float, int]:
        """Return (cpu seconds, rss bytes) of the process tree, raising the peak of every open window."""
        try:
            processes = [self._root, *self._root.children(recursive=True)]
        except psutil.Error:
            processes = [self._root]
        with self._lock:
            rss = 0
            for process in processes:
                try:
                    with process.oneshot():
                        times = process.cpu_times()
                        self._cpu_by_pid[process.pid] = times.user + times.system
                        rss += process.memory_info().rss
                except psutil.Error:
                    pass
            for window in self._windows:
                window.peak_rss = max(window.peak_rss, rss)
            return sum(self._cpu_by_pid.values()), rss

    def open_window(self) -> SampleWindow:
        cpu, rss = self.sample()
        window = SampleWindow(cpu_start=cpu, peak_rss=rss)
        with self._lock:
            self._windows.append(window)
        return window

    def close_window(self, window: SampleWindow) -> tuple[float, int]:
        """Return the CPU seconds spent and the peak RSS seen since `window` opened."""
        cpu, _ = self.sample()
        with self._lock:
            self._windows.remove(window)
        return cpu - window.cpu_start, window.peak_rss
