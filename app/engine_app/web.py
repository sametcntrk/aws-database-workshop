"""Flask web layer: one page per Engine App with Seed and Read actions.

ENGINE selects the adapter (engine_app/adapters/<ENGINE>.py); URL_PREFIX is the ALB path (/aurora, ...).
"""
import importlib
import logging
import os
import time
import traceback

from flask import Blueprint, Flask, jsonify, render_template, request

from . import domain

log = logging.getLogger("engine_app")


def load_adapter(engine):
    module = importlib.import_module(f"engine_app.adapters.{engine}")
    return module.ADAPTER()


def create_app():
    engine = os.environ.get("ENGINE", "aurora")
    prefix = os.environ.get("URL_PREFIX", f"/{engine}").rstrip("/")
    adapter = load_adapter(engine)
    bp = Blueprint("engine", __name__, template_folder="templates", static_folder="static", static_url_path="/static")

    @bp.get("/health")
    def health():
        return {"status": "ok", "engine": engine}

    @bp.get("/")
    def index():
        return render_template("index.html", a=adapter, prefix=prefix, sizes=list(domain.SIZES))

    @bp.post("/seed")
    def seed():
        size = request.args.get("size", "medium")
        started = time.perf_counter()
        try:
            ds = domain.build(size)
            result = adapter.seed(ds)
        except Exception as e:  # shown on the page: the workshop is about seeing what happens
            log.exception("seed failed")
            return jsonify(ok=False, error=f"{type(e).__name__}: {e}", trace=traceback.format_exc(limit=3)), 500
        return jsonify(ok=True, elapsed_ms=round((time.perf_counter() - started) * 1000), size=size,
                       summary=result.summary, operation=result.operation, counts=result.counts)

    @bp.get("/read")
    def read():
        started = time.perf_counter()
        try:
            result = adapter.read()
        except Exception as e:
            log.exception("read failed")
            return jsonify(ok=False, error=f"{type(e).__name__}: {e}", trace=traceback.format_exc(limit=3)), 500
        return jsonify(ok=True, elapsed_ms=round((time.perf_counter() - started) * 1000), columns=result.columns,
                       rows=[[_cell(v) for v in r] for r in result.rows], query=result.query, note=result.note,
                       images=result.images)

    app = Flask(__name__)
    app.register_blueprint(bp, url_prefix=prefix)
    return app


def _cell(v):
    if isinstance(v, (int, float, str)) or v is None:
        return v
    return str(v)


app = create_app()
