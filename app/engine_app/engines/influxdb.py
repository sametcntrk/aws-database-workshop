"""Timestream for InfluxDB - time-series: the operations Report Screen (warehouse sensors and orders per minute)."""
import json
from datetime import datetime, timedelta, timezone

from flask import jsonify, request
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from .. import catalog, trace
from ..base import env, secret

META = catalog.META["influxdb"]
PAGES = catalog.PAGES["influxdb"]
WINDOWS = {"1m", "5m", "15m", "1h"}
RANGES = {"-1h", "-6h", "-24h"}


def client():
    s = secret(env("INFLUX_SECRET_ARN"))
    return InfluxDBClient(url=env("INFLUX_URL"), username=s["username"], password=s["password"], org=env("INFLUX_ORG", "dbws"),
                          timeout=30_000)


def flux(op, query, note=None):
    with trace.call(op, query, {}) as t:
        with client() as c:
            tables = c.query_api().query(query, org=env("INFLUX_ORG", "dbws"))
        n = sum(len(tb.records) for tb in tables)
        t.result(items=n, note=note)
    return tables


def register(bp):
    @bp.get("/api/series")
    def api_series():
        measure = request.args.get("measure", "temperature")
        window = request.args.get("window", "15m")
        rng = request.args.get("range", "-6h")
        window = window if window in WINDOWS else "15m"
        rng = rng if rng in RANGES else "-6h"
        if measure == "orders":
            q = f'''from(bucket: "metrics")
  |> range(start: {rng})
  |> filter(fn: (r) => r._measurement == "orders")
  |> aggregateWindow(every: {window}, fn: sum, createEmpty: false)'''
            group = "channel"
        else:
            q = f'''from(bucket: "metrics")
  |> range(start: {rng})
  |> filter(fn: (r) => r._measurement == "warehouse_env" and r.sensor == "{'humidity' if measure == 'humidity' else 'temperature'}")
  |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)'''
            group = "warehouse"
        tables = flux("Flux query", q, note=f"aggregateWindow turns raw points into one value per {window}. "
                      "A wider window returns fewer points for the same time range.")
        series = {}
        for tb in tables:
            for rec in tb.records:
                series.setdefault(rec.values.get(group) or "all", []).append(
                    {"t": rec.get_time().isoformat(), "v": round(rec.get_value() or 0, 2)})
        return jsonify(trace.payload({"series": series, "window": window, "range": rng}))

    @bp.post("/api/orders-metric")
    def api_orders_metric():
        body = request.get_json(silent=True) or {}
        p = Point("orders").tag("channel", "workshop").field("count", int(body.get("count", 1))).time(datetime.now(timezone.utc), WritePrecision.S)
        with trace.call("write", f"POST /api/v2/write?bucket=metrics\n{p.to_line_protocol()}", {}) as t:
            with client() as c:
                c.write_api(write_options=SYNCHRONOUS).write(bucket=env("INFLUX_BUCKET", "metrics"), org=env("INFLUX_ORG", "dbws"), record=p)
            t.result(items=1, note="Line protocol: measurement, tags, fields and a timestamp in one line.")
        return jsonify(trace.payload({"written": 1}))


def seed(ds):
    bucket, org = env("INFLUX_BUCKET", "metrics"), env("INFLUX_ORG", "dbws")
    with trace.call("delete + write", "DELETE _measurement=\"warehouse_env\" OR \"orders\"; WRITE <line protocol> ...", {}) as t:
        with client() as c:
            for m in ("warehouse_env", "orders"):
                c.delete_api().delete(datetime(1970, 1, 1, tzinfo=timezone.utc), datetime.now(timezone.utc), f'_measurement="{m}"',
                                      bucket=bucket, org=org)
            points = [Point("warehouse_env").tag("warehouse", r["warehouse"]).tag("sensor", r["sensor"]).field("value", r["value"])
                      .time(r["time"], WritePrecision.S) for r in ds.readings]
            points += [Point("orders").tag("channel", "web").field("count", r["orders"]).time(r["time"], WritePrecision.S)
                       for r in ds.order_rate]
            c.write_api(write_options=SYNCHRONOUS).write(bucket=bucket, org=org, record=points)
        t.result(items=len(points))
    return [f"Wrote {len(ds.readings)} sensor points and {len(ds.order_rate)} orders-per-minute points."]


def reset_visitors():
    with client() as c:
        c.delete_api().delete(datetime(1970, 1, 1, tzinfo=timezone.utc), datetime.now(timezone.utc),
                              '_measurement="orders" AND channel="workshop"', bucket=env("INFLUX_BUCKET", "metrics"), org=env("INFLUX_ORG", "dbws"))
    return ["Deleted the order points from workshop checkouts."]


def status():
    return {"bucket": env("INFLUX_BUCKET", "metrics")}


SKIP = {"_start", "_stop", "_time", "_value", "result", "table", "_measurement", "_field"}


def _series_key(v):
    tags = {k: v[k] for k in sorted(v) if k not in SKIP and v[k] is not None}
    return v["_measurement"], tags, v["_field"]


def rng_q(q):
    return q.split("range(start: ", 1)[1].split(")", 1)[0]


def win_q(q):
    return q.split("every: ", 1)[1].split(",", 1)[0]


def learn_overview(lesson, focus):
    """101: each series (measurement + tags + field) as a shelf; each tile is one time window of the call's query."""
    rng = next((f for f in focus if f in RANGES), "-6h")
    window = next((f for f in focus if f in WINDOWS), "15m")
    measure = next((f for f in focus if f not in RANGES and f not in WINDOWS), "temperature")
    q = f'''from(bucket: "metrics")
  |> range(start: {rng})
  |> filter(fn: (r) => r._measurement == "warehouse_env" or r._measurement == "orders")
  |> aggregateWindow(every: {window}, fn: count, createEmpty: false)'''
    tables = flux("Flux query (count per window)", q)
    widened = None
    for wider, wwin in (("-24h", "1h"), ("-7d", "6h")):   # the seed data ends at seed time; look further back if the range is empty
        if any(tb.records for tb in tables):
            break
        widened, rng, window = wider, wider, wwin
        tables = flux("Flux query (count per window)", q.replace(f"range(start: {rng_q(q)})", f"range(start: {rng})")
                      .replace(f"every: {win_q(q)}", f"every: {window}"))
    groups, total = [], 0
    for tb in tables:
        recs = tb.records
        if not recs:
            continue
        m, tags, field = _series_key(recs[0].values)
        hit = (m == "orders") if measure == "orders" else (tags.get("sensor") == measure)
        label = f"{m} " + " ".join(f"{k}={v}" for k, v in tags.items())
        key = json.dumps([m, tags, field])
        total += sum(int(x.get_value() or 0) for x in recs)
        groups.append({"label": label, "items": [{"id": f"{key}|{x.get_time().isoformat()}|{window}",
                                                   "title": f"{x.get_time():%H:%M}: {x.get_value()} ham nokta", "hit": hit} for x in recs[-48:]]})
    groups.sort(key=lambda g: (not g["items"] or not g["items"][0]["hit"], g["label"]))
    note = (f" Seçtiğin aralıkta nokta yok (örnek veri yüklendiği anda bitiyor), bu yüzden {widened.lstrip('-')} geriye bakıldı."
            if widened else "")
    return {"title": "Timestream for InfluxDB: metrics bucket'ı", "text": f"Her raf bir seri (measurement + tag'ler). Her kare {window}'lık bir zaman penceresi; en yeni sağda." + note,
            "facts": [[len(groups), "seri"], [total, f"ham nokta ({rng.lstrip('-')} içinde)"], [window, "pencere"],
                      [sum(1 for g in groups if g["items"] and g["items"][0]["hit"]), "seri senin grafiğinde"]],
            "groups": groups, "hit_label": "Senin grafiğinin okuduğu seriler"}


def learn_item(lesson, item_id):
    key, ts, window = item_id.rsplit("|", 2)
    m, tags, field = json.loads(key)
    stop = datetime.fromisoformat(ts)
    minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "6h": 360}.get(window, 15)
    cond = " and ".join([f'r._measurement == "{m}"', f'r._field == "{field}"'] + [f'r.{k} == "{v}"' for k, v in tags.items()])
    q = f'''from(bucket: "metrics")
  |> range(start: {(stop - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")}, stop: {stop.strftime("%Y-%m-%dT%H:%M:%SZ")})
  |> filter(fn: (r) => {cond})'''
    pts = [(x.get_time(), x.get_value()) for tb in flux("Flux query (raw points)", q) for x in tb.records]
    vals = [v for _, v in pts if v is not None]
    tag_lp = "".join(f",{k}={v}" for k, v in tags.items())
    rec = {"measurement": m, "tags": tags, "field": field,
           "pencere": {"başlangıç": (stop - timedelta(minutes=minutes)).isoformat(), "bitiş": stop.isoformat()},
           "ham nokta sayısı": len(pts),
           "grafikteki tek değer": {"ortalama": round(sum(vals) / len(vals), 2) if vals else None, "toplam": round(sum(vals), 2) if vals else None,
                                    "en küçük": min(vals) if vals else None, "en büyük": max(vals) if vals else None},
           "ham noktalar (ilk 8)": [{"zaman": t.isoformat(), "değer": v} for t, v in pts[:8]]}
    if pts:
        rec["diskteki satır (line protocol)"] = f"{m}{tag_lp} {field}={pts[0][1]} {int(pts[0][0].timestamp())}"
    return {"title": f"{m}, {window} pencere", "sub": f"Bu kare, {len(pts)} ham noktanın tek bir değere indirgenmiş hali (aggregateWindow).",
            "record": rec, "marks": {"tags": "kept", "grafikteki tek değer": "kept"}}
