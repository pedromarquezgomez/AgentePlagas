import threading
from typing import Any

class RuntimeStatsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._provider = "llm"
        self._model = "unknown"
        self._requests = 0
        self._fallbacks = 0
        self._total_latency_ms = 0.0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._total_tokens = 0

    def record(
        self,
        provider: str,
        model: str | None,
        latency_ms: float,
        fallback_used: bool,
        tokens_used: dict[str, int] | None = None,
    ) -> None:
        with self._lock:
            self._provider = provider
            if model:
                self._model = model
            self._requests += 1
            if fallback_used:
                self._fallbacks += 1
            self._total_latency_ms += latency_ms
            if tokens_used:
                self._prompt_tokens += tokens_used.get("prompt_tokens") or 0
                self._completion_tokens += tokens_used.get("completion_tokens") or 0
                self._total_tokens += tokens_used.get("total_tokens") or 0

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            avg_latency = 0.0
            if self._requests > 0:
                avg_latency = self._total_latency_ms / self._requests
            return {
                "provider": self._provider,
                "model": self._model,
                "requests": self._requests,
                "fallbacks": self._fallbacks,
                "avg_latency_ms": round(avg_latency, 2),
                "prompt_tokens": self._prompt_tokens,
                "completion_tokens": self._completion_tokens,
                "total_tokens": self._total_tokens,
            }

    def reset(self) -> None:
        with self._lock:
            self._requests = 0
            self._fallbacks = 0
            self._total_latency_ms = 0.0
            self._model = "unknown"
            self._prompt_tokens = 0
            self._completion_tokens = 0
            self._total_tokens = 0


stats_collector = RuntimeStatsCollector()
