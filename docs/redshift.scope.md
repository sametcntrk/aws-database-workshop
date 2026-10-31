# Scope: Amazon Redshift Serverless (redshift)

status: verified domain-map row, first page in model 2 (weighted R1 "Engine uyumu")
domain-map row: verified (feature list adapted, see below)
date: 2026-10-31

Page: `app/engine_app/templates/e2e/redshift.tr.html` (Turkish only; replaces the older Turkish page on main). The old English `redshift.html` stays untouched and keeps its legacy simulations `decide_report`, `decide_checkout`, `rowcol`, `zonemap`, `dist`. Data: `REDSHIFT_W` at the end of `app/engine_app/e2e_usecases_w.py`, registered as `USECASES_W["redshift"]` and `PAGE_SVC["redshift"] = "rs"`. New entries: `CATEGORY`/`LINK` for `ath` (Athena) and `rsp` (Redshift provisioned) in the block, `SVC["rsp"] = "Redshift provisioned"` in `e2e_sims.py`. Simulations: `redshift()` in `e2e_sims.py` adds for `lang == "tr"` the five `weighted_scorecard` sims (`w_reporting`, `w_attribution`, `w_clicks`, `w_logs`, `w_forecast`) and the new mechanism sim `update` (`rs_update`). New teaching tables: `rs_customers`, `rs_dict`, `rs_encoded` (computed from `RS_ROWS`). Reading time in `e2e/index.yaml`: 150 minutes. Check: `check_usecases.py --app <abs app> redshift`.

Twin rule: Redshift Serverless (`rs`, the page's service) and Redshift provisioned (`rsp`) run one engine and get the same R1 points on every card where both appear (3, 5, 8, 10).

## Part A topic and the everyday picture (A1)

- Category in one general term: the columnar data warehouse (OLAP next to OLTP)
- Everyday picture: an election night count (400 ballot reports; one party's line per report; a team that splits the work and adds sub-totals)
- The trade: few columns of billions of rows in seconds / a single row by key is slower than OLTP; compression / an update is a mark and an append with background clean-up; parallel slices / distribution is a design decision; separate from checkout / data is a copy and lags the source (about 30 s in this workshop)

## Feature list Ö1–Ö8

The domain-map row lists F1 column storage and compression · F2 distribution key and slices · F3 sort key and zone maps · F4 MPP · F5 SQL with window functions · F6 Spectrum and data sharing · F7 zero-ETL ingestion · F8 serverless RPUs. The page generalizes them so that Part A stays product-neutral: compression is its own feature, MPP and distribution are one, Spectrum, data sharing and serverless capacity are one ("compute and storage separation"), and pre-computation (materialized view, result cache) is a feature, because two cards depend on it.

| No | Feature | Defining section | Official sentence (URL) | Limit |
|---|---|---|---|---|
| Ö1 | Columnar storage | A3 | "Amazon Redshift is a columnar store database and organizes data in 1 MB blocks" (https://aws.amazon.com/blogs/big-data/getting-the-most-out-of-your-analytics-stack-with-amazon-redshift/) | a single row touches every column block |
| Ö2 | Per-column compression | A4 | RAW for sort key columns, AZ64 for numeric and timestamp, LZO for VARCHAR (https://aws.amazon.com/blogs/big-data/migrating-from-vertica-to-amazon-redshift/); live: bytedict, az64, lzo, none | random values do not compress |
| Ö3 | Sort key and zone map | A5 | "tracks the minimum and maximum column values stored on each block and can skip blocks that don't apply to the predicate range" (https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-sort-key.html) | one order per table; not an index |
| Ö4 | MPP and distribution key | A6 | AUTO, EVEN, KEY, ALL (https://docs.aws.amazon.com/redshift/latest/dg/c_choosing_dist_sort.html); "Your fact table can have only one distribution key" (https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-best-dist-key.html); leader node, compute nodes, slices (https://docs.aws.amazon.com/prescriptive-guidance/latest/query-best-practices-redshift/data-warehouse-arch-components.html) | one key; skew; planning cost per query |
| Ö5 | Analytic SQL | A8 | PostgreSQL-like SQL, window functions; SUPER + PartiQL (https://docs.aws.amazon.com/redshift/latest/dg/super-overview.html) | no inverted index; point lookups pay planning |
| Ö6 | Materialized view and result cache | A8 | incremental refresh (https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-refresh.html); result cache on the leader node, invalidated by DML (https://docs.aws.amazon.com/redshift/latest/dg/c_challenges_achieving_high_performance_queries.html) | writes invalidate the cache |
| Ö7 | Bulk load and change transfer | A7 | "Using individual INSERT statements to populate a table might be prohibitively slow" (https://docs.aws.amazon.com/redshift/latest/dg/r_INSERT_30.html); deletes "marked for deletion, but not removed", automatic VACUUM DELETE (https://docs.aws.amazon.com/redshift/latest/dg/t_Reclaiming_storage_space202.html); zero-ETL "within seconds of being written" (https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/zero-etl.html), measured about 30 s here; source tables need a primary key (https://docs.aws.amazon.com/redshift/latest/mgmt/zero-etl.reqs-lims.html); streaming ingestion (https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-streaming-ingestion.html); constraints "not enforced", NOT NULL enforced (https://docs.aws.amazon.com/redshift/latest/dg/t_Defining_constraints.html) | no TTL; no unique/FK enforcement |
| Ö8 | Compute and storage separation | A9 | one RPU = 16 GB, default base 128 RPU, from 4 RPU (https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-capacity.html); RPU-hours per second, 60-second minimum, Spectrum and concurrency scaling included (https://aws.amazon.com/redshift/pricing/); no compute charge when no queries run (https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing-on-demand.html); data sharing "live and available to all warehouses as soon as a write transaction is committed" (https://docs.aws.amazon.com/redshift/latest/dg/datashare-overview.html) | 60 s minimum; external tables have no zone maps |

Other facts: recovery points every 30 minutes, kept 24 hours; restore between Serverless and provisioned (https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-snapshots-recovery-points.html). SNAPSHOT (default) and SERIALIZABLE isolation (https://docs.aws.amazon.com/redshift/latest/dg/c_serial_isolation.html). VACUUM skips the sort phase above 95 % sorted (https://docs.aws.amazon.com/redshift/latest/dg/r_VACUUM_command.html). Minimum table size formula (https://repost.aws/knowledge-center/redshift-cluster-storage-space). Redshift ML (https://docs.aws.amazon.com/redshift/latest/gsg/machine-learning.html). Data API (https://docs.aws.amazon.com/redshift/latest/mgmt/data-api.html). Row-level security (https://docs.aws.amazon.com/redshift/latest/dg/t_rls.html); views for fine-grained access in data sharing (https://aws.amazon.com/blogs/big-data/amazon-redshift-data-sharing-best-practices-and-considerations/). Athena "$5 per TB of data scanned", 10 MB minimum (https://docs.aws.amazon.com/whitepapers/latest/big-data-analytics-options/amazon-athena.html). SYS_SERVERLESS_USAGE charged_seconds are RPU-seconds (https://docs.aws.amazon.com/redshift/latest/dg/SYS_SERVERLESS_USAGE.html).

Prices (AWS Price List API, eu-central-1, read 2026-10-31): Serverless 0.451 USD/RPU-hour on demand, 0.352 USD with a 1-year reservation; managed storage 0.0256 USD/GB-month; ra3.large 0.649 USD/h, ra3.xlplus 1.298 USD/h, ra3.4xlarge 3.894 USD/h on demand and 1.6939 USD/h with a 3-year no-upfront reservation.

## All cases per concept

| Section | Concept | Cases (including the impossible one) |
|---|---|---|
| A1 | query shape and its place | key read/write; multi-table write with rules; scan + group; join many sources; recent days; thousands of single-row writes (do not); word search (not a warehouse job) |
| A2 | arranging facts and dimensions | star; snowflake; flat denormalized; source copy as is; unique/FK enforcement on the fact table (mostly none) |
| A3 | query shape in a column store | 2 of 8 columns; SELECT *; one row by key; insert one row; update in place (no); 3 of 100 columns |
| A4 | data and encoding | few short texts (dictionary); numbers and dates (AZ64/delta); long texts (LZO/ZSTD); constant or increasing; sort key column (RAW); random values (barely compresses); row store (no per-column encoding) |
| A5 | filter and zone map | range on sort key; equality; second column of compound key; unsorted column; function on column; unsorted region; exact row (cannot); word in text (cannot) |
| A6 | distribution | KEY; EVEN; ALL; AUTO; two big tables on different keys (cannot both be local); skewed key |
| A7 | write paths | COPY; INSERT SELECT/CTAS; zero-ETL; streaming; single INSERT at high rate (do not); UPDATE; DELETE; TTL (none); rule enforcement (none) |
| A8 | analytic question and tool | group total; join; top N per group; previous value; moving average; repeated heavy query; new question; one row a thousand times in 2 s (not a warehouse job) |
| A9 | place of data and compute | both in warehouse; data in S3 + warehouse query; data in S3 + query engine; two compute one data; variable load; whole data in one machine's memory (not needed); classic coupled cluster |
| B5 | load shape and bill | few queries a day; three busy days a month; minute dashboard in office hours; flat 24/7; sub-second queries; runaway query without limits |

## Anatomy list and colors

- Core data structures: fact table, dimension table, column block, zone map (min/max per block), slice, sort key, distribution key, update mark (deleted row + appended row).
- Colors: sort key yellow (`c-pk`), distribution key blue (`c-sk`), other columns grey; stated in A5 (and the A6 anatomy caption), used in the A6 and B1 anatomies, the A8 ROW_NUMBER table, the `update` simulation (order_date yellow).
- Three views: raw (live `sales` rows, `pg_table_def`, `svv_table_info`), anatomy (A6 teaching rows, B1 live rows), mapping sentences (after each anatomy).

## Matrix products (A10)

PostgreSQL (Aurora), Athena (Trino on S3), Redshift.

## R1 catalog of the domain

Domain: database. Catalog: `R1_CATALOG` (VM, ŞE, EY, OY, TA, DA, YD, AO), accepted on 2026-10-29. Every card uses four sub-items.

## Use cases (M2): candidates, weights, results (model 2)

The domain-map titles were kept where they make a decision; three titles were adapted: "product analytics funnels" became the click stream card that the Keyspaces page already scores (same workload, same points), "inventory forecasting inputs" became the flat 24/7 card where the provisioned twin wins, "executive dashboards" kept, "financial close" got adjusting entries that must obey rules (so Aurora wins R1).

| No | Use case | Candidates (best fit first) | R1 sub-items | R1 weight | Totals /100 | sim |
|---|---|---|---|---|---|---|
| 1 | Sales reporting over three years (= Aurora card 6) | Redshift, Aurora, OpenSearch | DA, EY, AO, OY | 48 | 93,6 · 63,8 · 62,0 | w_reporting |
| 2 | Marketing attribution | Redshift, Athena, Aurora | EY, DA, AO, OY | 46 | 90,0 · 85,4 · 61,4 (race) | w_attribution |
| 3 | Financial close | Redshift, Aurora, Redshift provisioned | EY, DA, ŞE, TA | 42 | 88,2 · 73,8 · 71,2 (Aurora wins R1 35,2 vs 34,2) | none |
| 4 | Click stream (= Keyspaces card 7) | Keyspaces, DynamoDB, Redshift | EY, DA, OY, YD | 46 | 77,0 · 76,6 · 62,0 (Redshift third) | w_clicks |
| 5 | Data sharing between teams and accounts | Redshift, Athena, Redshift provisioned | EY, DA, AO, TA | 44 | 94,8 · 80,6 · 79,8 | none |
| 6 | ML feature preparation | Redshift, Athena, Aurora | EY, DA, OY, AO | 44 | 91,4 · 78,8 · 59,4 | none |
| 7 | Log aggregation and search | OpenSearch, Athena, Redshift | EY, VM, YD, DA | 44 | 85,6 · 64,4 · 62,4 (Redshift third) | w_logs |
| 8 | Inventory forecasting inputs, flat 24/7 | Redshift provisioned, Redshift, Aurora | EY, DA, AO, OY | 46 | 93,0 · 89,8 · 68,0 (race; R1 equal 44,2) | w_forecast |
| 9 | Executive dashboards | Redshift, OpenSearch, Aurora | EY, DA, AO, OY | 44 | 88,8 · 66,0 · 64,4 | none |
| 10 | Ad-hoc analyst queries on S3 | Athena, Redshift, Redshift provisioned | EY, DA, ŞE, AO | 42 | 95,4 · 90,2 · 71,0 (R1 equal 38,4) | none |

- Clear losses of Redshift: card 4 (point lookup, Keyspaces), card 7 (word search, OpenSearch). Lost to its twin: card 8. Lost to Athena with equal R1: card 10.
- Another engine wins R1 but loses the total: card 3 (Aurora 35,2 vs Redshift 34,2; rules enforced by the engine).
- "Both together": cards 1 (Aurora + Redshift), 3 (adjustments could stay in Aurora), 4 (Keyspaces + Redshift), 6 (Redshift + SageMaker AI), 7 (OpenSearch + S3/Athena), 10 (Athena lake + Redshift reports).
- Services checked and left out: DynamoDB on cards 1–3, 5–10 (no GROUP BY, scans; only a source via zero-ETL); ElastiCache on card 9 (live counters only, no history SQL; ElastiCache card 5 already pairs a live hour in memory with history in Redshift); Timestream for InfluxDB on card 7 (metrics, not log text); EMR / Glue Spark on card 6 (not a database of the workshop; SageMaker named as the "both together" partner); Neptune (no relation traversal in any card).
- ElastiCache card 5 (real-time counters) mentions Redshift only as the place of the hourly history, not as a candidate, so no score had to be kept from it.

## Known traps (handled explicitly in Part A)

1. Single-row INSERT at high rate → A7 "do not" row, quiz rs-q5, card 4 OY.
2. UPDATE/DELETE leave marks; VACUUM → A7 flow, B4 `update` simulation, live `unsorted` 91,58.
3. Constraints not enforced → A2 last row, A7 row and ask box, card 3 ŞE, recall rs-r3.
4. Zone map is not an index; word search → A5 cannot rows, M3, card 7.
5. One distribution key per table → A6 cannot row, B3 ask box.
6. 60-second minimum per query; flat 24/7 load → B5 table, cards 3, 8, 10.
7. Zero-ETL lag (about 30 s here, "within seconds" in the docs) and primary-key requirement → A7 card, B4 live, M5.
8. Small table occupies many 1 MB blocks → B1 live `size` 2629 with the minimum table size formula.

## Live artifacts

| Structure | Artifact | How it was taken (2026-10-31, read only, Redshift Data API, workgroup dbws, database dev) |
|---|---|---|
| table, distribution, sort key, encoding | `svv_table_info` row of `sales` | `SELECT "table", diststyle, sortkey1, encoded, tbl_rows, size, unsorted FROM svv_table_info WHERE "table"='sales'` |
| column blocks and encodings | `pg_table_def` | `SELECT "column", type, encoding, distkey, sortkey FROM pg_table_def WHERE tablename='sales'` |
| fact rows | first five rows by date | `SELECT * FROM sales ORDER BY order_date, order_id, product_id LIMIT 5` |
| report | Q1 answer | admin report query |
| plan | EXPLAIN of the March query | `EXPLAIN SELECT category, sum(amount) … WHERE order_date BETWEEN …` |
| result cache | two runs of Q1 | `sys_query_history` (125 ms, then 3,2 ms with result_cache_hit = true) |
| zero-ETL | integration state and newest copied order | `svv_integration`, `aurora_live.public.orders` |
| cost | three days of compute | `sys_serverless_usage` (charged_seconds) |

`stv_blocklist` and `svv_diskusage` (block-level zone maps) are not readable in this Serverless workgroup ("permission denied"); the zone map is shown with the teaching blocks instead.

## Teaching data

`RS_ROWS` (8 order lines of 8 columns, real Lale Market ids), `rs_customers` (4 customers from the Aurora teaching copy), `rs_dict` and `rs_encoded` (dictionary encoding of `category`, computed), `RS_BLOCKS_SORTED` / `RS_BLOCKS_UNSORTED` (zone maps), the teaching hash `customer number % 2` (slices).

## Images

All from `e2e/images.yaml` (records existed): `redshift-row-storage.png`, `redshift-column-storage.png`, `redshift-architecture.png`, `redshift-zero-etl.png` (AWS documentation), `redshift-star-schema.png` (Wikimedia Commons, CC BY-SA 3.0). Each was looked at on 2026-10-31. Own drawings with the page data: dictionary encoding flow (A4, Ö2), zone map blocks (A5, Ö3), A6 anatomy and slice placement (Ö4), update flow (A7, Ö7), ROW_NUMBER table (A8, Ö5/Ö6). Feature → picture: Ö1 row/column storage images; Ö2 dictionary flow; Ö3 zone map blocks; Ö4 anatomy + slices + architecture image; Ö5 star schema + ROW_NUMBER table; Ö6 result cache live artifact; Ö7 update flow + zero-ETL image; Ö8 architecture image.

## Reader simulation

`docs/redshift.reader-report.md` (2026-10-31): 15 findings, all closed. Point changes after the reader: card 5 Athena R1.2 8→9 and R1.4 7→9 (Athena second, 80,6), card 7 Athena R1.2 8→7 and R5 5→7, Redshift R1.2 7→8. Cards 1 and 4 keep the points of the Aurora and Keyspaces pages; only their texts changed.
