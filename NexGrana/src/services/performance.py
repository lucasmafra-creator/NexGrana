"""Medição leve de performance sem telemetria remota.

Os dados ficam somente em memória nesta versão. Eles servem para profiling local
antes/depois e nunca carregam conteúdo financeiro.
"""
from __future__ import annotations

from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class Metric:
    name: str
    duration_ms: float


class PerformanceMonitor:
    def __init__(self, max_samples: int = 120):
        self._samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=max_samples))

    @contextmanager
    def measure(self, name: str):
        start = perf_counter()
        try:
            yield
        finally:
            self.record(name, (perf_counter() - start) * 1000)

    def record(self, name: str, duration_ms: float):
        self._samples[str(name)].append(max(0.0, float(duration_ms)))

    def summary(self, name: str) -> dict:
        values = sorted(self._samples.get(str(name), ()))
        if not values:
            return {"count": 0, "p50_ms": None, "p95_ms": None, "max_ms": None}
        def pct(q: float):
            idx = min(len(values) - 1, max(0, round((len(values) - 1) * q)))
            return round(values[idx], 2)
        return {
            "count": len(values),
            "p50_ms": pct(.50),
            "p95_ms": pct(.95),
            "max_ms": round(values[-1], 2),
        }

    def all_summaries(self) -> dict:
        return {k: self.summary(k) for k in sorted(self._samples)}
