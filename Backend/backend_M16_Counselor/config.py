"""Where M16 keeps things. Every path and port can be overridden from the
environment; nothing here is a secret."""

import os
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent

#: PORTS.txt: M16 is API 8116, web 5216.
PORT = int(os.getenv("BACKEND_PORT", "8116"))
DATABASE_URL = os.getenv("M16_DATABASE_URL", f"sqlite:///{(BACKEND / 'dev.db').as_posix()}")
MODULE_JSON = ROOT / "module.json"
#: The four people a student can talk to (data, not code: adding a fifth is
#: an entry here, a face from M11's make_faces.py and a line in its cast).
COUNSELORS_FILE = Path(__file__).with_name("counselors.json")
#: How long an upstream call may take before the talk does without it.
UPSTREAM_TIMEOUT_S = float(os.getenv("M16_UPSTREAM_TIMEOUT", "8"))
#: The most interviews one talk covers, and the choices a student has.
EVERY_CHOICES = (1, 2, 3)
