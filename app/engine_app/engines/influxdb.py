"""Timestream for InfluxDB - time-series: the operations Report Screen (warehouse sensors and orders per minute)."""
from datetime import datetime, timezone

from flask import jsonify, request
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from .. import trace
from ..base import env, secret
from . import page

META = {
    "id": "influxdb", "name": "Amazon Timestream for InfluxDB", "data_type": "Semi-structured", "category": "Time-series",
    "auth": "Password (Secrets Manager)", "via": "InfluxDB endpoint (data subnet, HTTPS 8086)", "section": "Operations",
    "model": "bucket metrics\n  warehouse_env  tags: warehouse, sensor   field: value   every 5 minutes\n"
             "  orders         tags: channel              field: count   every minute",
}
PAGES = [page("ops", "ops", "Operations", "/admin/ops")]
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
