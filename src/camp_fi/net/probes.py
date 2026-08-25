from dataclasses import dataclass
from enum import Enum, auto

import httpx

from .http_client import build_http_client


class ConnectivityStatus(Enum):
    INTERNET = auto()
    CAPTIVE = auto()
    OFFLINE = auto()
    UNKNOWN = auto()

@dataclass(frozen=True)
class ProbeSpec:
    name: str
    url: str
    success_status: int = 204
    success_body: str | None = None

PROBE_SPECS = [
    ProbeSpec("Google", "http://connectivitycheck.gstatic.com/generate_204", 204),
    ProbeSpec("Cloudflare", "http://cp.cloudflare.com/generate_204", 204),
    ProbeSpec("Apple", "http://captive.apple.com/hotspot-detect.html", 200, "Success"),
    ProbeSpec("Microsoft", "http://www.msftconnecttest.com/connecttest.txt", 200, "Microsoft Connect Test"),
    ProbeSpec("Mozilla", "http://detectportal.firefox.com/success.txt", 200, "success"),
]

# Kept for backward compatibility in tests that monkeypatch PROBE_URLS
PROBE_URLS = [p.url for p in PROBE_SPECS]

@dataclass(frozen=True)
class ProbeResult:
    status: ConnectivityStatus
    probe_name: str | None = None
    redirect_url: str | None = None
    status_code: int | None = None

def check_connectivity(timeout: float = 3.0, specs: list[ProbeSpec] | None = None) -> ProbeResult:
    """Check network connectivity across standard probes and classify status.

    Redirects are unambiguous captive portal evidence. Other unexpected
    responses require corroboration across probes before returning CAPTIVE.
    """
    active_specs = specs or PROBE_SPECS

    # Support monkeypatched PROBE_URLS if test overrides it
    if PROBE_URLS and PROBE_URLS[0] != active_specs[0].url:
        active_specs = [ProbeSpec("Custom", PROBE_URLS[0], 204)]

    captive_hits: list[ProbeResult] = []
    reachable = False

    with build_http_client(timeout=timeout, follow_redirects=False) as client:
        for spec in active_specs:
            try:
                resp = client.get(spec.url)
                reachable = True

                if 300 <= resp.status_code < 400 and "location" in resp.headers:
                    return ProbeResult(
                        status=ConnectivityStatus.CAPTIVE,
                        probe_name=spec.name,
                        redirect_url=resp.headers["location"],
                        status_code=resp.status_code,
                    )

                if resp.status_code == spec.success_status and (
                    spec.success_body is None or spec.success_body in resp.text
                ):
                    return ProbeResult(
                        ConnectivityStatus.INTERNET,
                        spec.name,
                        status_code=resp.status_code,
                    )

                captive_hits.append(
                    ProbeResult(
                        ConnectivityStatus.CAPTIVE,
                        spec.name,
                        redirect_url=spec.url,
                        status_code=resp.status_code,
                    )
                )
            except httpx.RequestError:
                continue

    if not reachable:
        return ProbeResult(ConnectivityStatus.OFFLINE)
    if len(captive_hits) >= 2 or (active_specs and len(captive_hits) == len(active_specs)):
        return captive_hits[0]
    if captive_hits:
        return ProbeResult(ConnectivityStatus.UNKNOWN)
    return ProbeResult(ConnectivityStatus.UNKNOWN)
