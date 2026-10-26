"""Admin Console API, served by every Engine App for its own Engine.

The browser sends the instructor key in the X-Admin-Key header. The key lives in the dbws/admin secret.
"""
import hmac
import time

from flask import jsonify, request

from . import domain, simlimit, trace
from .base import env, secret


def _authorized():
    key = request.headers.get("X-Admin-Key", "")
    expected = secret(env("ADMIN_SECRET_ARN"))["key"]
    return bool(key) and hmac.compare_digest(key, expected)


def register(bp, engine):
    """engine: the Engine module (META, seed(ds), reset_visitors(), status())."""

    def guard():
        if not _authorized():
            return jsonify(ok=False, error="The admin key is not correct."), 403
        trace.configure(engine.META)
        return None

    @bp.post("/api/admin/seed")
    def admin_seed():
        refused = guard()
        if refused:
            return refused
        size = request.args.get("size", "medium")
        started = time.perf_counter()
        result = engine.seed(domain.build(size))
        return jsonify(trace.payload({"summary": result, "size": size,
                                      "elapsed_ms": round((time.perf_counter() - started) * 1000)}))

    @bp.post("/api/admin/reset-visitors")
    def admin_reset():
        refused = guard()
        if refused:
            return refused
        return jsonify(trace.payload({"summary": engine.reset_visitors()}))

    @bp.post("/api/admin/simulation")
    def admin_sim():
        refused = guard()
        if refused:
            return refused
        simlimit.set_enabled(request.args.get("enabled", "true") == "true")
        return jsonify(trace.payload(simlimit.status()))

    @bp.get("/api/admin/status")
    def admin_status():
        refused = guard()
        if refused:
            return refused
        return jsonify(trace.payload({"engine": engine.status(), "simulation": simlimit.status()}))
