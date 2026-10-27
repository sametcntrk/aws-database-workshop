"""Flask app factory. ENGINE selects the Engine module (engine_app/engines/<ENGINE>.py).

Each Engine App serves:
  - its Storefront Section and Report Screen pages on friendly paths (/cart, /search, /admin/reports, ...)
  - its API, static files and health check under /<engine>/...
The browser composes pages from several Engine Apps (docs/adr/0002-browser-composes-storefront.md).
"""
import importlib
import logging
import os
import traceback
from functools import lru_cache
from pathlib import Path

import yaml
from flask import Blueprint, Flask, jsonify, render_template, request
from jinja2 import TemplateNotFound

from . import admin, simlimit, trace, visitor

log = logging.getLogger("engine_app")
HERE = Path(__file__).parent

# Storefront navigation. Every Engine App renders the same header, so the site feels like one shop.
NAV = [
    {"href": "/", "label": "Home", "engine": "docdb"},
    {"href": "/search", "label": "Search", "engine": "opensearch"},
    {"href": "/deals", "label": "Flash deal", "engine": "elasticache"},
    {"href": "/stores", "label": "Stores", "engine": "opensearch"},
    {"href": "/orders", "label": "My orders", "engine": "aurora"},
    {"href": "/account/activity", "label": "My activity", "engine": "keyspaces"},
    {"href": "/seller", "label": "Seller panel", "engine": "s3"},
]
REPORTS = [
    {"href": "/admin/reports", "label": "Sales reports", "engine": "redshift"},
    {"href": "/admin/orders", "label": "Order report", "engine": "aurora"},
    {"href": "/admin/live", "label": "Live leaderboard", "engine": "elasticache"},
    {"href": "/admin/ops", "label": "Operations", "engine": "influxdb"},
    {"href": "/admin/graph", "label": "Customer graph", "engine": "neptune"},
    {"href": "/admin", "label": "Admin Console", "engine": "docdb"},
]


@lru_cache(maxsize=None)
def tutorials(engine):
    path = HERE / "tutorials" / f"{engine}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


@lru_cache(maxsize=None)
def lessons(engine):
    """101 lessons of one Engine (lessons/<engine>.yaml, Turkish). Every Engine App has every file, so any app can list all."""
    path = HERE / "lessons" / f"{engine}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def find_lesson(engine, method, api, op):
    """The lesson for a clicked call: the longest matching "[METHOD ]/api/path" wins, then the Engine op name."""
    best = None
    for lid, lesson in lessons(engine).items():
        for key in lesson.get("apis", []):
            m, _, path = key.rpartition(" ")
            if (not m or m == method) and api.startswith(path) and (best is None or len(path) > best[0]):
                best = (len(path), lid)
    if best:
        return best[1]
    return next((lid for lid, lesson in lessons(engine).items() if op in lesson.get("ops", [])), None)


ENGINE_IDS = ["docdb", "opensearch", "dynamodb", "aurora", "redshift", "elasticache", "keyspaces", "influxdb", "neptune", "s3"]


def lesson_index():
    return [{"engine": e, "id": lid, "title": l["title"]} for e in ENGINE_IDS for lid, l in lessons(e).items()]


@lru_cache(maxsize=None)
def journey():
    return yaml.safe_load((HERE / "tutorials" / "journey.yaml").read_text(encoding="utf-8"))


def create_app():
    engine_id = os.environ.get("ENGINE", "docdb")
    engine = importlib.import_module(f"engine_app.engines.{engine_id}")
    meta = engine.META
    prefix = f"/{engine_id}"

    app = Flask(__name__, static_folder=None)
    app.json.sort_keys = False   # 101 lessons show records in their real field order
    bp = Blueprint("engine", __name__, static_folder="static", static_url_path="/static")

    @bp.before_request
    def _trace():
        trace.configure(meta)

    @bp.get("/health")
    def health():
        return {"status": "ok", "engine": engine_id}

    @bp.get("/api/meta")
    def api_meta():
        return jsonify(trace.payload({**meta, "simulation": simlimit.status()}))

    @bp.get("/learn")
    def learn():
        """101 lesson for one Engine call. The browser gives the clicked call (a localStorage key) to the page."""
        op = request.args.get("op", "")
        lid = request.args.get("lesson") or find_lesson(engine_id, request.args.get("method", "GET"), request.args.get("api", ""), op)
        lesson = lessons(engine_id).get(lid)
        ctx = dict(meta=meta, prefix=prefix, op=op, lesson=lid, content=lesson, index=lesson_index())
        if not lesson:
            return render_template("learn/missing.html", **ctx)
        return render_template(lesson.get("template") or "learn/lesson.html", **ctx)

    if hasattr(engine, "learn_overview"):
        @bp.get("/api/learn/overview")
        def learn_overview():
            """Big picture for a lesson: every record (or a sample) as a tile, grouped; `focus` marks the records of the call."""
            focus = [f for f in request.args.get("focus", "").split(",") if f]
            return jsonify(trace.payload(engine.learn_overview(request.args.get("lesson", ""), focus)))

        @bp.get("/api/learn/item")
        def learn_item():
            """One record of the big picture, with its nested structure."""
            return jsonify(trace.payload(engine.learn_item(request.args.get("lesson", ""), request.args.get("id", ""))))

    engine.register(bp)
    admin.register(bp, engine)

    @bp.errorhandler(simlimit.SimulationRefused)
    def _refused(e):
        return jsonify(ok=False, error=str(e), trace=[]), 429

    @bp.errorhandler(Exception)
    def _error(e):
        log.exception("API error")
        from flask import g
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}", detail=traceback.format_exc(limit=2),
                       trace=getattr(g, "trace", [])), 500

    app.register_blueprint(bp, url_prefix=prefix)

    def page_view(page):
        def view(**kwargs):
            trace.configure(meta)
            return render_template(
                f"pages/{page['template']}.html", meta=meta, page=page, args=kwargs, prefix=prefix,
                tutorial=tutorials(engine_id).get(page["id"], {}), journey=journey(), nav=NAV, reports=REPORTS,
                personas=visitor.PERSONAS)
        view.__name__ = f"page_{page['id']}"
        return view

    for page in engine.PAGES:
        for path in page["paths"]:
            app.add_url_rule(path, view_func=page_view(page), endpoint=f"{page['id']}:{path}")
    return app


app = create_app()
