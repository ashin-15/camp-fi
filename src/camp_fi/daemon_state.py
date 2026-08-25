from __future__ import annotations
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import LoginResult
from .net.probes import ConnectivityStatus

if TYPE_CHECKING:
    from .config import ProfileConfig

@dataclass
class DaemonState:
    active_profile: str | None = None
    backoff_seconds: int = 5
    max_backoff_seconds: int = 300
    keepalive_interval: int | None = 300
    keepalive_url: str | None = None
    last_keepalive_time: float = 0
    last_status: ConnectivityStatus | None = None
    consecutive_failures: int = 0

    def reset_backoff(self):
        self.backoff_seconds = 5
        self.consecutive_failures = 0

    def increase_backoff(self):
        self.backoff_seconds = min(self.backoff_seconds * 2, self.max_backoff_seconds)
        self.consecutive_failures += 1

    def is_keepalive_due(self, now: float) -> bool:
        if not self.keepalive_interval:
            return False
        return (now - self.last_keepalive_time) >= self.keepalive_interval

    def update_from_login(self, result: LoginResult, now: float, profile: ProfileConfig | None = None):
        if result.succeeded:
            self.reset_backoff()
            if result.keepalive:
                # Clamp keepalive interval between 45 and 3600 seconds
                self.keepalive_interval = max(45, min(result.keepalive.interval_seconds, 3600))
                self.keepalive_url = result.keepalive.url
            elif profile:
                if profile.keepalive_interval_seconds is not None:
                    self.keepalive_interval = max(45, min(profile.keepalive_interval_seconds, 3600))
                if profile.keepalive_url is not None:
                    self.keepalive_url = profile.keepalive_url
            self.last_keepalive_time = now
        else:
            self.increase_backoff()

    def to_dict(self) -> dict:
        return {
            "active_profile": self.active_profile,
            "backoff_seconds": self.backoff_seconds,
            "consecutive_failures": self.consecutive_failures,
            "last_status": self.last_status.name if self.last_status else None,
            "keepalive_interval": self.keepalive_interval,
            "last_keepalive_time": self.last_keepalive_time,
            "updated_at": time.time(),
        }
