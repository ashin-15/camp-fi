from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

class LoginStatus(Enum):
    SUCCESS = auto()
    UNSUPPORTED_PORTAL = auto()
    AUTH_FAILED = auto()
    NETWORK_ERROR = auto()
    PROTOCOL_ERROR = auto()

@dataclass(frozen=True)
class KeepaliveSpec:
    url: str
    interval_seconds: int

@dataclass(frozen=True)
class LoginResult:
    status: LoginStatus
    adapter_name: str | None = None
    keepalive: KeepaliveSpec | None = None
    message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is LoginStatus.SUCCESS

@dataclass
class PreparedLogin:
    data: dict[str, Any]
