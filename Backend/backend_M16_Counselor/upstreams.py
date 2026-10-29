"""What M16 reads from other modules, always on the student's behalf.

    M06   the student's interviews (newest first) and each one's report
    M04   the profile (name, weekly goal, drives), mastery and trajectory

Every call forwards the student's identity (`ai_core.guard.identity_headers`),
so M06 and M04 apply their own rule about who may see what — M16 is never
given more than the student could read themselves. Every failure is `None`,
never a raise: a module that is down narrows the talk, it does not stop it
(spec §10), and `/v1/deps` names which.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Any, Protocol

from ai_core import service
from ai_core.dependencies import DependencyRegistry
from ai_core.guard import identity_headers

from . import config

log = logging.getLogger("uvicorn.error")


class Reader(Protocol):
    """What a talk reads. `Upstreams` over HTTP; a fake in the tests."""

    def interviews(self, candidate_id: str) -> list[dict[str, Any]] | None: ...

    def report(self, candidate_id: str, session_id: str) -> dict[str, Any] | None: ...

    def profile(self, candidate_id: str) -> dict[str, Any] | None: ...

    def mastery(self, candidate_id: str) -> dict[str, Any] | None: ...

    def trajectory(self, candidate_id: str) -> dict[str, Any] | None: ...


@lru_cache(maxsize=1)
def registry() -> DependencyRegistry:
    return DependencyRegistry.from_manifest(config.MODULE_JSON)


class Upstreams:
    def __init__(self, timeout_s: float = config.UPSTREAM_TIMEOUT_S) -> None:
        self.timeout_s = timeout_s

    def _get(self, module: str, path: str, candidate_id: str) -> Any | None:
        dep = registry().get(module)
        if dep is None:
            return None
        request = urllib.request.Request(
            f"{dep.base_url.rstrip('/')}{path}",
            headers={
                **identity_headers(candidate_id),
                **service.headers(),
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            log.info("M16: %s %s answered %s", module, path, exc.code)
        except Exception as exc:  # noqa: BLE001 - an absent module narrows the talk
            log.info("M16: %s %s unreachable: %s", module, path, exc)
        return None

    def interviews(self, candidate_id: str) -> list[dict[str, Any]] | None:
        got = self._get(
            "M06", f"/v1/interviews/by-candidate/{candidate_id}?limit=120", candidate_id
        )
        return got if isinstance(got, list) else None

    def report(self, candidate_id: str, session_id: str) -> dict[str, Any] | None:
        sid = urllib.parse.quote(session_id)
        got = self._get("M06", f"/v1/interviews/{sid}/report", candidate_id)
        return got if isinstance(got, dict) else None

    def profile(self, candidate_id: str) -> dict[str, Any] | None:
        got = self._get("M04", f"/v1/candidates/{candidate_id}/profile", candidate_id)
        return got if isinstance(got, dict) else None

    def mastery(self, candidate_id: str) -> dict[str, Any] | None:
        got = self._get("M04", f"/v1/candidates/{candidate_id}/mastery", candidate_id)
        return got if isinstance(got, dict) else None

    def trajectory(self, candidate_id: str) -> dict[str, Any] | None:
        got = self._get("M04", f"/v1/candidates/{candidate_id}/trajectory", candidate_id)
        return got if isinstance(got, dict) else None
