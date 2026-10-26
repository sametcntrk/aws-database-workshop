"""Cost guard for Load Simulation: a fixed request ceiling, one run per Engine at a time,
three runs per Visitor per hour, and an on/off switch for the Admin Console.

State is a small JSON file shared by the gunicorn workers of this Engine App.
"""
import fcntl
import json
import os
import time
from contextlib import contextmanager

MAX_REQUESTS = 2000
RUNS_PER_HOUR = 3
STATE = "/tmp/lm-simulation.json"


class SimulationRefused(Exception):
    pass


@contextmanager
def _locked():
    fd = os.open(STATE, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        raw = f.read()
        state = json.loads(raw) if raw.strip() else {"enabled": True, "running": False, "runs": {}}
        yield state
        f.seek(0)
        f.truncate()
        f.write(json.dumps(state))


def status():
    with _locked() as s:
        return {"enabled": s["enabled"], "running": s["running"], "max_requests": MAX_REQUESTS,
                "runs_per_hour": RUNS_PER_HOUR}


def set_enabled(enabled):
    with _locked() as s:
        s["enabled"] = bool(enabled)


@contextmanager
def run(visitor, requested):
    """Reserve a simulation slot. Raises SimulationRefused with a reason the UI shows to the Visitor."""
    n = max(1, min(int(requested), MAX_REQUESTS))
    now = time.time()
    with _locked() as s:
        if not s["enabled"]:
            raise SimulationRefused("The instructor turned Load Simulation off.")
        if s["running"] and now - s.get("started", 0) < 300:
            raise SimulationRefused("Another simulation runs on this Engine now. Try again in a minute.")
        recent = [t for t in s["runs"].get(visitor, []) if now - t < 3600]
        if len(recent) >= RUNS_PER_HOUR:
            raise SimulationRefused(f"You can start {RUNS_PER_HOUR} simulations per hour. Try again later.")
        s["runs"][visitor] = recent + [now]
        s["running"], s["started"] = True, now
    try:
        yield n
    finally:
        with _locked() as s:
            s["running"] = False
