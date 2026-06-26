from __future__ import annotations

import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock

import yaml

from llm_service.config import get_config_dir, get_settings

GROQ_PREFIX = "groq/"


def _load_groq_limits() -> tuple[int, int, dict[str, dict[str, int]]]:
    path = get_config_dir() / "groq_limits.yaml"
    if not path.exists():
        return 30, 1000, {}
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    plan = get_settings().groq_plan
    plans = cfg.get("plans") or {}
    block = plans.get(plan) if isinstance(plans.get(plan), dict) else {}
    if block:
        return (
            int(block.get("default_rpm", 30)),
            int(block.get("default_rpd", 1000)),
            block.get("models") or {},
        )
    # Legacy flat file (single tier)
    return int(cfg.get("default_rpm", 30)), int(cfg.get("default_rpd", 1000)), cfg.get("models") or {}


def _utc_today_start() -> datetime:
    n = datetime.now(timezone.utc)
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


class GroqRateLimiter:
    def __init__(self):
        self._lock = Lock()
        self._default_rpm, self._default_rpd, self._models = _load_groq_limits()
        self._per_model: dict[str, tuple[deque[float], list[float]]] = {}

    def _get_limits(self, model: str) -> tuple[int, int]:
        entry = self._models.get(model) or {}
        return int(entry.get("rpm", self._default_rpm)), int(entry.get("rpd", self._default_rpd))

    def _get_or_create(self, model: str) -> tuple[deque[float], list[float]]:
        with self._lock:
            if model not in self._per_model:
                self._per_model[model] = (deque(maxlen=2000), [])
            return self._per_model[model]

    def wait_if_needed(self, model: str) -> None:
        if not model.startswith(GROQ_PREFIX):
            return
        rpm, rpd = self._get_limits(model)
        q, day_ts = self._get_or_create(model)
        day_start = _utc_today_start().timestamp()
        while True:
            with self._lock:
                now = time.time()
                while q and q[0] < now - 60.0:
                    q.popleft()
                while day_ts and day_ts[0] < day_start:
                    day_ts.pop(0)
                if len(q) < rpm and len(day_ts) < rpd:
                    return
                wait = 1.0
                if len(q) >= rpm and q:
                    wait = max(wait, 60.0 - (now - q[0]))
                if len(day_ts) >= rpd:
                    wait = max(wait, (day_start + 86400) - now)
            time.sleep(min(wait, 1.0))

    def record_request(self, model: str) -> None:
        if not model.startswith(GROQ_PREFIX):
            return
        q, day_ts = self._get_or_create(model)
        now = time.time()
        with self._lock:
            q.append(now)
            day_ts.append(now)


_limiter: GroqRateLimiter | None = None


def get_groq_rate_limiter() -> GroqRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = GroqRateLimiter()
    return _limiter
