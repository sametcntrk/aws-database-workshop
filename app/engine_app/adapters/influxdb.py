"""Timestream for InfluxDB - time-series: warehouse sensor readings with window aggregation."""
from datetime import datetime, timezone

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from ..base import Adapter, ReadResult, SeedResult, env, secret

MODEL = """\
bucket  metrics
measurement  warehouse_env
  tags    warehouse=IST-1|ANK-1|FRA-1|BER-1, sensor=temperature|humidity
  field   value (float)
  time    every 5 minutes

Line protocol: warehouse_env,warehouse=IST-1,sensor=temperature value=22.4 1761000000"""

FLUX = """\
from(bucket: "metrics")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "warehouse_env" and r.sensor == "temperature")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> group(columns: ["warehouse"])
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 6)"""


class InfluxDb(Adapter):
    engine_id = "influxdb"
    title = "Amazon Timestream for InfluxDB"
    data_type = "Semi-structured"
    category = "Time-series"
    domain_slice = "depo sensör ve metrik verisi"
    why = ("Zaman damgalı ölçümler (sensör, metrik, fiyat) için: zaman aralığına göre filtre, pencere ortalaması, "
           "downsampling ve saklama süresi yerleşik gelir. Timestream for LiveAnalytics yeni müşterilere kapalı olduğu "
           "için yönetilen InfluxDB kullanılıyor.")
    model = MODEL

    def _client(self):
        s = secret(env("INFLUX_SECRET_ARN"))
        return InfluxDBClient(url=env("INFLUX_URL"), username=s["username"], password=s["password"],
                              org=env("INFLUX_ORG", "dbws"), timeout=30_000)

    def seed(self, ds):
        bucket, org = env("INFLUX_BUCKET", "metrics"), env("INFLUX_ORG", "dbws")
        with self._client() as client:
            client.delete_api().delete(datetime(1970, 1, 1, tzinfo=timezone.utc), datetime.now(timezone.utc),
                                       '_measurement="warehouse_env"', bucket=bucket, org=org)
            points = [Point("warehouse_env").tag("warehouse", r["warehouse"]).tag("sensor", r["sensor"])
                      .field("value", r["value"]).time(r["time"], WritePrecision.S) for r in ds.readings]
            client.write_api(write_options=SYNCHRONOUS).write(bucket=bucket, org=org, record=points)
        return SeedResult(
            summary=["Eski warehouse_env ölçümleri silindi (delete API)",
                     f"{len(points)} ölçüm yazıldı: 4 depo × 2 sensör, 5 dakikada bir"],
            operation="DELETE predicate _measurement=\"warehouse_env\"\n"
                      "WRITE  warehouse_env,warehouse=IST-1,sensor=temperature value=22.4 <unix-seconds>  ...",
            counts={"points": len(points)})

    def read(self):
        rows = []
        with self._client() as client:
            for table in client.query_api().query(FLUX, org=env("INFLUX_ORG", "dbws")):
                for rec in table.records:
                    rows.append((rec.values.get("warehouse"), rec.get_time(), round(rec.get_value(), 2)))
        return ReadResult(["warehouse", "hour", "mean_temperature"], rows, FLUX,
                          note="aggregateWindow ham 5 dakikalık ölçümleri saatlik ortalamaya indirir; SQL'de bunun için GROUP BY + date_trunc gerekirdi.")


ADAPTER = InfluxDb
