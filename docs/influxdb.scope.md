# Scope: Amazon Timestream for InfluxDB (influxdb)

status: verified domain-map row, first page of the engine in model 2 (weighted R1 "Engine uyumu")
date: 2026-10-31

Page: `app/engine_app/templates/e2e/influxdb.tr.html` (Turkish only; replaces the older short Turkish page). The English `influxdb.html` (model 1) stays untouched and keeps its legacy simulations `decide_metrics`, `decide_orders`, `series`, `window`, `retention` and the data `IX_LINES`, `IX_RAW`, `IX_SHARDS`. Data: `INFLUXDB_W` at the end of `app/engine_app/e2e_usecases_w.py`, registered as `USECASES_W["influxdb"]` and `PAGE_SVC["influxdb"] = "ix"` (the existing short name "Timestream for InfluxDB"). New entries: `CATEGORY`/`LINK` for `ix3` in the block, `SVC["ix3"] = "Timestream for InfluxDB 3"` in `e2e_sims.py`. Simulations: `influxdb()` adds for `lang == "tr"` the five `weighted_scorecard` sims (`w_warehouse`, `w_metrics`, `w_sensor`, `w_ticks`, `w_laststate`) and the new mechanism sim `cardinality` (`ix_cardinality`, teaching table `ix_orders`). Reading time in `e2e/index.yaml`: 140 minutes. Check: `check_usecases.py --app <abs app> influxdb`.

## Twin decision

- **InfluxDB 2 and InfluxDB 3 are not twins.** Same data model and line protocol, different engine: TSM files + Flux/InfluxQL against Apache Arrow + DataFusion + Parquet on S3 + SQL/InfluxQL ("InfluxDB 3 is a complete architectural redesign. It replaces the TSM ... storage engine with Apache Arrow ..., Apache DataFusion ..., and Apache Parquet for columnar storage on Amazon S3", https://docs.aws.amazon.com/timestream/latest/developerguide/faq-general.html). Rule "Same data model, different engine" (decisions.md): R1 scored separately on every card. Candidate `ix3` = Timestream for InfluxDB 3, Enterprise edition in the cards (Core: single node, no compaction, recent data "typically around 3 days").
- **InfluxDB 2 has no twin service.** Single-AZ, Multi-AZ standby and the read replica cluster are deployment options of one engine and one service; a card chooses the option its story needs. So the twin rule "at least one card has the twin" does not apply; `ix3` appears on cards 4, 5, 6, 7.

## Part A topic and the everyday picture (A1)

- Category: the time series database. Everyday picture: an electricity meter (one number, overwritten) against the bill table (one row per 15 minutes, appended, asked by ranges).
- Trade: tens of thousands of small appends / no update in place (same instant overwrites); compression per series / tag cardinality must stay bounded; window questions in one query / no JOIN, FK, transaction; retention by setting / deletion by time range, not by record.

## Feature list Ö1–Ö8

Domain-map row: F1 write points with time · F2 measurement, tag set, series · F3 window aggregation · F4 downsampling and retention · F5 last value queries · F6 continuous tasks · F7 Flux/InfluxQL · F8 Multi-AZ instances. Adapted so Part A stays product-neutral: F7 (query language) and F8 (Multi-AZ, a service option) are not category features; storage by time and per-series compression and the read path by range + tag are features, because cards depend on them.

| No | Feature | Defining section | Official sentence (URL) | Limit |
|---|---|---|---|---|
| Ö1 | Append time-stamped points | A2, A6 | duplicate point: "identifies unique data points by their measurement, tag set, and timestamp", "creates a union of the old and new field sets", "uses the field value of the new point" (https://docs.influxdata.com/influxdb/v2/write-data/best-practices/duplicate-points/); line protocol (https://docs.influxdata.com/influxdb/v2/reference/syntax/line-protocol/) | no update in place, no increment, no transaction |
| Ö2 | Measurement, tag, series | A3 | "High series cardinality is a primary driver of high memory usage for many database workloads"; "Tags containing highly variable information like unique IDs ... lead to a large number of series" (https://docs.influxdata.com/influxdb/v2/write-data/best-practices/resolve-high-cardinality/) | unbounded ids cannot be tags |
| Ö3 | Time partitions, per-series compression | A4 | WAL "ensures data is durable in case of an unexpected failure"; "TSM files store compressed series data in a columnar format"; "groups field values by series key, and then orders those field values by time"; "only stores differences (or deltas)"; TSI "As data cardinality ... grows, queries read more series keys and become slower" (https://docs.influxdata.com/influxdb/v2/reference/internals/storage-engine/); shard groups and default durations 1 h / 1 d / 7 d (https://docs.influxdata.com/influxdb/v2/reference/internals/shards/) | data on the instance's disk, max 16 TiB (https://docs.aws.amazon.com/prescriptive-guidance/latest/timestream-for-influxdb-well-architected-framework/reliability.html) |
| Ö4 | Range + tag read | A5 | Flux range() required on a bucket (engine code and Flux docs) | no text search, field filters read every point |
| Ö5 | Window aggregation | A7 | aggregateWindow (engine code `engines/influxdb.py`) | joins weak, no SQL in InfluxDB 2 |
| Ö6 | Last value and selectors | A5 | last() | no cache in InfluxDB 2; InfluxDB 3 Last Value Cache "under 10ms for last-value queries" (https://docs.aws.amazon.com/timestream/latest/developerguide/core-and-enterprise-versions.html) |
| Ö7 | Retention and downsampling | A8 | retention service deletes shard groups past the period (shards page above); downsampling task with to() (https://docs.influxdata.com/influxdb/v2/process-data/common-tasks/downsample-data/) | per bucket, not per point |
| Ö8 | Tasks and checks | A9 | tasks, checks, notification endpoints (InfluxDB 2 docs); Flux "is in maintenance mode and is not supported in InfluxDB 3" (https://docs.influxdata.com/flux/v0/future-of-flux/) | time-driven; no change stream; no learned detection |

Other AWS facts: Multi-AZ "synchronous standby replica in a different Availability Zone", failover "typically 60–120 seconds"; internal backups 24 h, snapshots on deletes 30 days via Support (reliability pillar URL above). Standby "cannot be configured to accept database read activity" (https://aws.amazon.com/timestream/faqs/). Read replica clusters, tip data, Marketplace licence (https://docs.aws.amazon.com/timestream/latest/developerguide/timestream-for-influx-working-read-replica.html). Instance sizing table (https://docs.aws.amazon.com/timestream/latest/developerguide/timestream-for-influxdb.html). Storage types 3K (min 20 GiB), 12K and 16K (min 400 GiB) (https://aws.amazon.com/timestream/pricing/). InfluxDB 3: object storage on S3, 11 nines, min 200 GB, Enterprise licence per vCPU-hour via Marketplace, node classes (https://docs.aws.amazon.com/timestream/latest/developerguide/influxdb3.html); SQL primary, InfluxQL for compatibility (https://docs.aws.amazon.com/timestream/latest/developerguide/faq-data-operations.html); Enterprise 1–4 writers, 0–13 readers, 1 compactor, up to 15 nodes (https://aws.amazon.com/blogs/database/features-and-workflows-with-amazon-timestream-for-influxdb-3/). InfluxDB 3 accepts SQL and InfluxQL, InfluxDB 2 Flux and InfluxQL (https://aws.amazon.com/timestream/features/). Timestream for LiveAnalytics closed to new customers from June 2025 (https://aws.amazon.com/about-aws/whats-new/2025/05/aws-service-changes/). CloudWatch retention (3 h for <60 s, 15 d 1-min, 63 d 5-min, 455 d 1-h) and custom metric price 0.30 USD: taken from the accepted OpenSearch page (cards 7, 10).

Prices (AWS Price List API, AmazonTimestream, eu-central-1, effective 2026-08-01, read 2026-10-31): db.influx.medium 0.145 USD/h Single-AZ, 0.289 Multi-AZ; large 0.289 / 0.577; 2xlarge 1.155 / 2.311; 4xlarge 2.311 / 4.621; storage InfluxIOIncluded T1 0.119 / 0.238 USD/GB-mo, T2 0.417 / 0.834, T3 0.596 / 1.192; InfluxDB 3 cluster node db.influx.large 0.289 USD/h, db.influxIOIncluded.large 0.319; InfluxDB object storage 0.0245 USD/GB-mo.

## All cases per concept

| Section | Concept | Cases (impossible one in bold on the page) |
|---|---|---|
| A1 | data shape and its place | time series; only last state; rules (cannot); event text search (cannot); join over years; counters |
| A2 | point shape | one field; several fields; no tag; field types; type change (rejected); no field (cannot); no timestamp |
| A3 | tag or field | warehouse; sensor; measured number; truck id (count it); order id (do not tag); free text (neither) |
| A4 | storage | in order; late point; slow values; random values (barely compress); high cardinality; update in place (cannot) |
| A5 | read paths | range + tag; range only; field filter; last value; no range (cannot in Flux); text (cannot); join (weak) |
| A6 | write paths | new; batch; late; same instant same field; same instant other field; range delete; delete by field value (cannot); increment (cannot); transaction (none) |
| A7 | window functions | mean; sum; max/min; last; quantile; derivative; empty window; window > range; grouping; learned normal (not in engine) |
| A8 | end of data | no retention; not expired; expired; late old point; downsampling; per-point retention (cannot); raw from summary (cannot) |
| A9 | scheduled jobs | downsampling; threshold; deadman; send out; react to each write (none); learned anomaly (none) |

## Anatomy and colors

Measurement + tags yellow (`c-pk`), timestamp blue (`c-sk`), fields grey; stated in A2 and used in the A2 anatomy, the B1 live anatomy, the A5 table and the A5 flow. Three views: raw (live line protocol and Flux answers), anatomy (A2 teaching rows, B1 live rows), mapping sentences (after each anatomy).

## Matrix products (A10)

Prometheus, TimescaleDB, InfluxDB 2 (InfluxDB 3 explained in text and M5).

## Use cases (M2)

| No | Use case | Candidates (best fit first) | R1 sub-items (weight) | Totals | sim |
|---|---|---|---|---|---|
| 1 | Lale Market warehouses and stores, 1,000 sensors | ix, CloudWatch, Aurora (existing) | VM, EY, DA, YD, AO (48) | 85,5 · 83,3 · 78,1 (race) | w_warehouse |
| 2 | Application metrics (= OpenSearch card 7) | ix, CloudWatch, OpenSearch | VM, EY, YD (42) | 84,8 · 83,6 · 66,4 (race) | w_metrics |
| 3 | Wind farm sensors (= Keyspaces card 2) | Keyspaces, ix, DynamoDB | EY, VM, DA, YD (50) | 91,2 · 88,4 · 85,2 (race; ix wins R1 50 vs 42) | w_sensor |
| 4 | Fleet telemetry, last value + history | ix3, ix, DynamoDB | EY, VM, DA, YD (46) | 89,5 · 83,1 · 77,6 | — |
| 5 | Factory monitoring, migration of an existing InfluxDB | ix, ix3, CloudWatch | VM, EY, YD, AO (46) | 91,3 · 77,2 · 65,2 | — |
| 6 | Financial ticks, 3 years | ix3, Redshift, ix | EY, DA, VM, YD (44) | 91,6 · 80,2 · 65,0 (ix third) | w_ticks |
| 7 | Smart meter billing analytics | Redshift, ix3, ix | EY, DA, OY, VM (46) | 96 · 77,6 · 47,8 (ix third) | — |
| 8 | Anomaly detection on order flow (= OpenSearch card 10) | OpenSearch, ix, CloudWatch | AO, EY, VM (42) | 88 · 70 · 69,6 | — |
| 9 | Last state of IoT devices (= DynamoDB card 5) | DynamoDB, Keyspaces, ix | EY, OY, YD (45) | 99 · 94 · 53 (ix third) | w_laststate |
| 10 | Real-time counters (= ElastiCache card 5) | ElastiCache, DynamoDB, ix | OY, VM, EY, YD (50) | 90 · 68 · 64 (ix third) | — |

- Copied cards read their points from the source card at import time (`_same`), so a change on the owner page changes both pages; reasons of the other candidates are the source reasons without the other page's feature numbers; reasons, head-to-heads for `ix` and verdicts are new.
- Clear losses of ix: 6, 7, 8, 9, 10. Lost close race: 3. Lost to ix3: 4.
- Another engine wins R1 but loses the total: card 3 (ix wins R1, Keyspaces wins).
- "Both together": 3, 6, 7, 9, 10.
- Existing system: card 1 Aurora (Lale Market cluster), card 5 the factory's own InfluxDB, card 8 the OpenSearch domain.
- Left out: Timestream for LiveAnalytics (closed to new customers), Amazon Managed Service for Prometheus (not a workshop service; CloudWatch plays the role), Athena (cards 6, 7).

## Cross-page consistency (decisions.md rules 10–15, checked with main 7585eee)

`tools/cross_page_reductions.py` (main 7585eee, with `influxdb` added to PAGES) on a copy of the app with main's data plus this block: totals unchanged against main. Changes made for consistency: card 6 Redshift no-TTL 5→6 (Redshift page grade, 4 off), freshness moved from R2 to R1 · EY (rule 12: EY 9→6, R2 5→9 with the fixed-capacity 1 point of rule 13), R4 7→8 (stream layer 1 + refresh plan 1); card 7 Redshift R2 9→10 and InfluxDB 3 R2 8→9 (rule 13: planning goes to R4). Aurora on card 1: no-TTL grade 6 (same as DynamoDB card 1); DA 5 with a sentence on why the Aurora page's scan grades (6–7) do not apply. Grades of ix written once in the M2 summary (R3 failover 1/2/3, R4 5/4/2/6, R5 Multi-AZ standby 2 / sized for a peak or growing storage 4–5 / years on SSD 6–7, R2 0/1/2–5). After the reader: CloudWatch retention on the 0–3 band when a part of the want is not met (card 1: 3, card 5: 2); OpenSearch card 7's CloudWatch YD 8 and its head-to-head numbers are listed for a joint fix by the owner page.

## Known traps (handled in Part A)

1. Unbounded id in a tag → A3 table, quiz ix-q2, B2 `cardinality` sim, card 10.
2. No update in place / increment → A6 table and flow, cards 9, 10.
3. Retention is per bucket and drops whole shard groups → A8, B4 sim.
4. Last value is a query, not a cache (InfluxDB 2) → A5, Ö6, card 4.
5. Flux not in InfluxDB 3 → A9 ask, B3, card 5.
6. Multi-AZ failover 60–120 s loses unbuffered writes → C2, cards 3, 9.

## Live artifacts (2026-10-31, read only)

| Structure | Artifact | How |
|---|---|---|
| series list, cardinality | 10 series, 2,278 points in 24 h | GET /influxdb/api/learn/overview?focus=-24h,1h,temperature |
| point, series raw | IST-1 temperature 10:00–11:00, 12 points, line protocol | GET /influxdb/api/learn/item |
| window query | Q1 answer, 15-minute means per warehouse | GET /influxdb/api/series?measure=temperature&window=15m&range=-24h |
| orders window | 10:00–10:15 sum 1,135, mean 75,67 | GET /influxdb/api/learn/item (orders) |
| instance | GetDbInstance dbws-influxdb (medium, T1 20 GiB, Multi-AZ, 1c/1b) | AWS API timestream-influxdb, eu-central-1 |
| definition | `AWS::Timestream::InfluxDBInstance` | cloudformation/workshop.yaml |

No live write was made (the checkout write is shown from the code).

## Images

From `e2e/images.yaml` (records existed, looked at 2026-10-31): `influxdb-raw-series.png`, `influxdb-windows.png` (InfluxData docs, MIT), `influxdb-derived-series.png` (Wikimedia Commons, CC0). Own drawings with the page data: A1 meter/bill flow, A2 anatomy, A4 write flow and shard groups, A5 read flow, A6 duplicate point flows, A8 two-bucket flow, A9 check flow, B1 live anatomy. Feature → picture: Ö1 A6 flows; Ö2 A2/B1 anatomy + raw series image; Ö3 A4 flow and parts; Ö4 A5 flow; Ö5 windows image; Ö6 B1 live anatomy and A5 flow; Ö7 A8 flow; Ö8 A9 flow.

## Reader simulation

`docs/influxdb.reader-report.md` (2026-10-31): 15 findings, all closed. Point changes after the reader: card 1 CloudWatch YD 4→3 (83,3), card 5 CloudWatch YD 5→2 (65,2) and InfluxDB R5 9→8 (91,3), card 6 InfluxDB R3 8→7 (65,0). Copied cards keep the points of their owner pages.
