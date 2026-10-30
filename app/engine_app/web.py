"""Flask app factory. ENGINE selects the Engine module (engine_app/engines/<ENGINE>.py).

Each Engine App serves its API, static files, 101 lessons and health check under /<engine>/...

The DocumentDB Engine App is the default target of the load balancer. Paths that match no Engine rule come to it, so it
renders the site pages for all ten Engines (catalog.py has no database driver):
  /                                  Home hub with the three sections
  /e2etutorial, /e2etutorial/<e>     End-to-end tutorial of each Engine
  /guided-e-commerce-app/...         Lale Market with a locked, step-by-step mission
  /guided-e-commerce-app/perde-arkasi/<n>  the "Perde arkası" tab of Guided step n
The old friendly paths (/cart, /search, ...) and the removed Free e-commerce app (/free-e-commerce-app/...) redirect to the
Guided e-commerce app.
The browser composes pages from several Engine Apps (docs/adr/0002-browser-composes-storefront.md).
"""
import importlib
import logging
import os
import traceback
from functools import lru_cache
from pathlib import Path

import yaml
from flask import Blueprint, Flask, abort, jsonify, redirect, render_template, request
from jinja2 import TemplateNotFound

from . import admin, catalog, e2e_sims, simlimit, trace, visitor

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
def lessons(engine):
    """101 lessons of one Engine (lessons/<engine>.yaml, English). Every Engine App has every file, so any app can list all."""
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


ENGINE_IDS = catalog.ENGINE_IDS
SITE_ENGINE = "docdb"   # default ALB target: serves the site pages

# The e-commerce app. `base` is the path prefix of every shop link. (The Free e-commerce app was removed on 2026-10-31.)
MODES = {
    "guided": {"id": "guided", "base": "/guided-e-commerce-app", "label": "Guided e-commerce app"},
}
REMOVED_BASE = "/free-e-commerce-app"


def lesson_index():
    return [{"engine": e, "id": lid, "title": l["title"]} for e in ENGINE_IDS for lid, l in lessons(e).items()]


def app_code(spec):
    """A short excerpt of a real route of this repo for a Perde arkası page (panel.app_code).
    spec: {file: engines/<x>.py, func: <name>, lines: [{match, say}, ...]}. Each match is a piece of one source line, in order;
    a missing piece raises, so the page can never show code that drifted away from the repo."""
    src = (HERE / spec["file"]).read_text().splitlines()
    if "start" in spec:                                               # a block of a non-Python file (a page script): from a line to the end
        start = next(i for i, x in enumerate(src) if spec["start"] in x)
        base, end = len(src[start]) - len(src[start].lstrip()), len(src)
    else:
        start = next(i for i, x in enumerate(src) if x.lstrip().startswith(f"def {spec['func']}("))
        base, end, in_str = len(src[start]) - len(src[start].lstrip()), len(src), False
        for i in range(start + 1, len(src)):                          # the function ends at the first line back at its indent,
            if not in_str and src[i].strip() and len(src[i]) - len(src[i].lstrip()) <= base:   # not counting lines inside a """ or ''' string
                end = i
                break
            if (src[i].count('"""') + src[i].count("'''")) % 2:
                in_str = not in_str
    while start > 0 and src[start - 1].lstrip().startswith("@"):      # the route decorator says which URL the function answers
        start -= 1
    out, at = [], start
    for ln in spec["lines"]:
        i = next((i for i in range(at, end) if ln["match"] in src[i]), None)
        if i is None:
            raise ValueError(f"app_code: '{ln['match']}' not in {spec['file']}:{spec['func']}")
        out.append({"no": i + 1, "code": src[i][base:], "say": ln["say"], "gap": bool(out) and i > at,
                    "hl": ln.get("hl"), "tag": ln.get("tag")})
        at = i + 1
    return {**{k: v for k, v in spec.items() if k != "lines"}, "lines": out}


@lru_cache(maxsize=None)
def mission():
    """Steps of the Guided e-commerce app (tutorials/guided.yaml)."""
    return yaml.safe_load((HERE / "tutorials" / "guided.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def e2e_index():
    """The E2E tutorials in reading order (e2e/index.yaml)."""
    return yaml.safe_load((HERE / "e2e" / "index.yaml").read_text(encoding="utf-8"))


def e2e_glossary():
    """The terms of the E2E tutorials, sorted by term (e2e/glossary.yaml)."""
    g = yaml.safe_load((HERE / "e2e" / "glossary.yaml").read_text(encoding="utf-8"))
    return [{"id": k, **v} for k, v in sorted(g.items(), key=lambda kv: kv[1]["term"].lower())]


@lru_cache(maxsize=None)
def e2e_images():
    """Source and licence of each E2E tutorial image (e2e/images.yaml)."""
    return yaml.safe_load((HERE / "e2e" / "images.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def e2e_ui():
    """Labels of the E2E tutorial frame in each language (e2e/ui.yaml)."""
    return yaml.safe_load((HERE / "e2e" / "ui.yaml").read_text(encoding="utf-8"))


def page_owner():
    """{page id: Engine id} for all pages."""
    return {pg["id"]: e for e in ENGINE_IDS for pg in catalog.PAGES[e]}


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

    if hasattr(engine, "E2E"):
        @bp.get("/api/e2e/<qid>")
        def e2e_run(qid):
            """One fixed, read-only query of the E2E tutorial. The tutorial page shows the rows and the trace."""
            fn = engine.E2E.get(qid)
            if not fn:
                return jsonify(ok=False, error=f"No E2E query {qid!r} for this Engine.", trace=[]), 404
            return jsonify(trace.payload(fn()))

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

    def render_page(e, page, mode, kwargs):
        trace.configure(catalog.META[e])
        return render_template(
            f"pages/{page['template']}.html", meta=catalog.META[e], page=page, args=kwargs, prefix=f"/{e}", mode=mode,
            mission=mission() if mode["id"] == "guided" else None, owners=page_owner(),
            nav=NAV, reports=REPORTS, modes=MODES, personas=visitor.PERSONAS)

    def page_view(e, page, mode):
        def view(**kwargs):
            return render_page(e, page, mode, kwargs)
        view.__name__ = f"page_{mode['id']}_{page['id']}"
        return view

    def to_guided(rest="", **_):
        qs = request.query_string.decode()
        path = request.path[len(REMOVED_BASE):] if request.path.startswith(REMOVED_BASE) else request.path
        return redirect(MODES["guided"]["base"] + (path or "/") + (f"?{qs}" if qs else ""), 302)

    # Old friendly paths of this Engine: they go to the Guided e-commerce app.
    for page in engine.PAGES:
        for path in page["paths"]:
            if path != "/":
                app.add_url_rule(path, view_func=to_guided, endpoint=f"old:{path}")

    if engine_id == SITE_ENGINE:
        ctx = lambda **kw: dict(modes=MODES, engines=catalog.META, e2e=e2e_index(), images=e2e_images(), prefix=prefix, **kw)  # noqa: E731

        @app.get("/")
        def hub():
            return render_template("site/hub.html", mission_steps=len(mission()["steps"]), **ctx())

        # The removed Free e-commerce app: its links (bookmarks, old pages) open the same page of the Guided app.
        app.add_url_rule(REMOVED_BASE, view_func=to_guided, endpoint="removed:bare")
        app.add_url_rule(REMOVED_BASE + "/", view_func=to_guided, endpoint="removed:root")
        app.add_url_rule(REMOVED_BASE + "/<path:rest>", view_func=to_guided, endpoint="removed:any")

        @app.get("/e2etutorial")
        @app.get("/e2etutorial/")
        def e2e_home():
            return render_template("site/e2e_index.html", **ctx())

        @app.get("/e2etutorial/<eid>")
        def e2e_lesson(eid):
            if eid not in catalog.META and eid != "glossary":
                abort(404)
            entry = next((x for x in e2e_index()["lessons"] if x["id"] == eid), None)
            has_tr = (HERE / "templates" / "e2e" / f"{eid}.tr.html").exists()
            lang = "tr" if has_tr else "en"  # EN option removed: every page with a TR version shows TR
            name = f"e2e/{eid}.tr.html" if lang == "tr" else f"e2e/{eid}.html"
            return render_template(name, **ctx(eid=eid, entry=entry, meta=catalog.META.get(eid, {}),
                                               lang=lang, has_tr=has_tr, ui=e2e_ui()[lang],
                                               sims=e2e_sims.SIMS[eid](lang) if eid in e2e_sims.SIMS else {},
                                               sample_data=e2e_sims.tables(), usecases=e2e_sims.usecases(eid, lang),
                                               glossary=e2e_glossary() if eid == "glossary" else []))

        @app.get(MODES["guided"]["base"] + "/perde-arkasi/<int:n>")
        def perde_arkasi(n):
            """The "Perde arkası" of Guided step n, in its own tab (static/js/perde.js). The shop tab hands over the calls."""
            m = mission()
            if not 1 <= n <= len(m["steps"]):
                abort(404)
            spec = m["steps"][n - 1].get("panel", {}).get("app_code")
            code = [app_code(x) for x in (spec if isinstance(spec, list) else [spec])] if spec else None
            return render_template("site/perde.html", prefix=prefix, mission=m, n=n, step=m["steps"][n - 1], code=code,
                                   modes=MODES, mode=MODES["guided"])

        for mode in MODES.values():
            for e in ENGINE_IDS:
                for page in catalog.PAGES[e]:
                    for path in page["paths"]:
                        url = mode["base"] + (path if path != "/" else "/")
                        app.add_url_rule(url, view_func=page_view(e, page, mode), endpoint=f"{mode['id']}:{path}")
            app.add_url_rule(mode["base"], view_func=lambda base=mode["base"]: redirect(base + "/", 301),
                             endpoint=f"{mode['id']}:bare")
    return app


app = create_app()
