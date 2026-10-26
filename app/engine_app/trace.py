"""Behind-the-Scenes trace: every Engine call made while serving a request becomes one trace entry.

Usage inside an API handler:
    with trace.call("Query", "table.query(KeyConditionExpression=...)", {"pk": pk}) as t:
        resp = table.query(...)
        t.result(items=len(resp["Items"]), capacity="0.5 RCU", cost_usd=0.0000001)
The API returns `trace.payload(data)`, which adds the entries to the JSON body.
"""
import socket
import time
from contextlib import contextmanager

from flask import g

_IP = None


def app_ip():
    global _IP
    if _IP is None:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.20.0.1", 1))
            _IP = s.getsockname()[0]
            s.close()
        except OSError:
            _IP = "127.0.0.1"
    return _IP


class Entry:
    def __init__(self, op, request, params):
        self.data = {"op": op, "request": request, "params": params or {}, "ok": True}

    def result(self, **fields):
        """Add measured facts: items, capacity, cost_usd, note, explain, ..."""
        self.data.update({k: v for k, v in fields.items() if v is not None})


def configure(meta):
    """Called once per request with the Engine descriptor of this app."""
    g.trace_meta = meta
    g.trace = []


@contextmanager
def call(op, request, params=None):
    meta = getattr(g, "trace_meta", {})
    entry = Entry(op, request, params)
    entry.data.update({"engine": meta.get("name"), "auth": meta.get("auth"),
                       "path": f"EC2 {app_ip()} → {meta.get('via', '')}"})
    started = time.perf_counter()
    try:
        yield entry
    except Exception as e:
        entry.data.update({"ok": False, "error": f"{type(e).__name__}: {e}"[:500]})
        raise
    finally:
        entry.data["ms"] = round((time.perf_counter() - started) * 1000, 1)
        g.setdefault("trace", []).append(entry.data)


def payload(data=None, **extra):
    body = {"ok": True, "data": data, "trace": getattr(g, "trace", [])}
    body.update(extra)
    return body
