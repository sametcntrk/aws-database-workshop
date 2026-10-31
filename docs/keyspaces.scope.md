# Scope: Amazon Keyspaces (for Apache Cassandra) (keyspaces)

status: verified domain-map row, regenerated in model 2 (weighted R1 "Engine uyumu")
domain-map row: verified
date: 2026-10-30 (model 2); first version 2026-10-29 (model 1)

Page: `app/engine_app/templates/e2e/keyspaces.tr.html` (Turkish only; the old English `keyspaces.html` stays untouched and keeps its legacy `decide_feed` / `decide_report` and mechanism simulations). Data: `KEYSPACES_W` at the end of `app/engine_app/e2e_usecases_w.py` (model 2), registered as `USECASES_W["keyspaces"]` and `PAGE_SVC["keyspaces"] = "ks"`; the stories and R2–R5 texts come from `KS_USECASES` (model 1, kept). Simulations: `keyspaces()` in `app/engine_app/e2e_sims.py` adds `weighted_scorecard` for every card with a `sim` when `lang == "tr"` (`w_migration`, `w_sensor`, `w_clicks`, `w_fraud`, `w_reviews`); the mechanism simulations `partition`, `nokey`, `consistency`, `lwt` are unchanged. Check: `check_usecases.py --app <abs app> keyspaces`.

## Part A topic and the everyday picture (A1)

- Category in one general term: the wide-column database (partitions of sorted rows, CQL)
- Everyday picture: an insurance agency's filing cabinet, one drawer per customer, papers in date order, photocopies in other buildings
- The trade: same-time read and write by partition key / a question without it is refused or scans all; rows sorted at write time / one order per table; very high write rate over many machines / no JOIN, no GROUP BY, no multi-partition transaction; read freshness chosen per request / cheap reads may be a moment old; rows expire by themselves / deletes leave tombstones

## Feature list Ö1–Ö8 (F1–F8 of the domain map)

| No | Feature | Defining section | Official sentence (URL) | Limit |
|---|---|---|---|---|
| Ö1 | Read and write by partition key | A2, A5 | "By default, CQL only allows select queries that don't involve a full scan of all partitions" (https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html) | no question without the partition key; no aggregates in Keyspaces |
| Ö2 | Partitions by token, replicas, consistency levels | A4 | "A hash is computed from the partition key columns and that hash value defines the partition location" (https://cassandra.apache.org/doc/latest/cassandra/developing/cql/ddl.html); Keyspaces three copies, writes LOCAL_QUORUM, reads LOCAL_ONE or LOCAL_QUORUM (https://docs.aws.amazon.com/keyspaces/latest/devguide/consistency.html) | 3,000 RCU / 1,000 WCU per partition (https://docs.aws.amazon.com/keyspaces/latest/devguide/bp-partition-key-design.html) |
| Ö3 | Clustering columns: order and range inside the partition | A3, A5 | Keyspaces data model (https://docs.aws.amazon.com/keyspaces/latest/devguide/how-it-works.html) | one order per table; a changing value cannot be a clustering column |
| Ö4 | Column schema with flexible additions | A2 | ALTER TABLE ADD (https://docs.aws.amazon.com/keyspaces/latest/devguide/cql.ddl.table.html); row max 1 MB (https://docs.aws.amazon.com/keyspaces/latest/devguide/quotas.html) | primary key and type cannot change |
| Ö5 | Lightweight transactions (IF) | A6 | "no additional charge for using LWTs", failed condition consumes WRUs (https://docs.aws.amazon.com/keyspaces/latest/devguide/lightweight_transactions.html); Cassandra "non-negligible performance cost, because Paxos is used" | one partition only |
| Ö6 | Row and table TTL | A7 | "typically deletes expired data from storage within 10 days", "One TTL delete is consumed per KB" (https://docs.aws.amazon.com/keyspaces/latest/devguide/TTL.html) | TTL counts from write time; deletes are billed |
| Ö7 | Secondary index (limited) | A8 | CREATE INDEX: No, materialized views: No (https://docs.aws.amazon.com/keyspaces/latest/devguide/cassandra-apis.html); ScyllaDB global and local secondary indexes (https://docs.scylladb.com/manual/stable/features/index.html) | Keyspaces: one table per question |
| Ö8 | CDC streams | A9 | 24 hours retention, view types, exactly once (https://docs.aws.amazon.com/keyspaces/latest/devguide/cdc_how-it-works.html) | consumer via Streams API or KCL |

## All cases per concept

| Section | Concept | Cases (including the impossible one) |
|---|---|---|
| A2 | primary key forms | partition key only; partition key + clustering; composite partition key; no primary key (cannot) |
| A2 | values and column list | type fits; wrong type (refused); value missing (stores nothing); primary key column missing (refused); column not in table (refused); change type or primary key (cannot); size limit |
| A3 | two rows and their keys | same/same (one row, upsert); same/different; different/same; different/different |
| A3 | role of the clustering column | none; time DESC; time + id; name; frequently changing value (not suitable); composite partition key to bound a partition |
| A4 | token and partition | partition key only; with clustering; composite key; node added; hot partition; read without partition key (cannot) |
| A4 | consistency level (RF 3) | QUORUM+QUORUM; QUORUM+ONE; write ONE/ANY (not in Keyspaces); ALL (not in Keyspaces); EACH_QUORUM (not in Keyspaces) |
| A5 | read paths | full primary key; partition key; partition key + range; part of a composite partition key (cannot); range on partition key (cannot); IN; regular column only (refused, ALLOW FILTERING); no WHERE; aggregates (none in Keyspaces) |
| A5 | clustering conditions | equal; range; equal + range; skip first clustering column (no); reverse; order by regular column (no); LIKE (no); LIMIT |
| A6 | write paths | new key; existing key (upsert, no error); update missing row; counter; LWT; delete row; delete partition/range; delete by regular column (cannot); change primary key (cannot); batch; multi-partition conditional transaction (cannot) |
| A6 | tombstone sources | row delete; partition/range delete; NULL write; TTL expiry; key change; append-only table (none) |
| A7 | expiry | none; table default; write TTL; renewed; expired read; storage deletion; cost; by data date (cannot) |
| A8 | a question and its path | has partition key; other column frequent (second table); Cassandra index with partition key; rare (analysis copy); unknown questions (weak point); ALLOW FILTERING in production (do not) |
| A9 | what goes into the stream | insert/update; delete; TTL expiry; batch; read (nothing); two writes; nobody reads (24 h) |
| B4 | partition growth | bounded by TTL; composite key by month; write sharding; second question |

## Anatomy list and colors

- Core data structures: keyspace, table, partition, row, partition key, clustering column (plus composite partition key and the second table)
- Colors: partition key yellow (`c-pk`), clustering column blue (`c-sk`), other columns grey; stated before the A2 anatomy; the simulations of the Keyspaces section color `user_id` and the next column the same way

## Matrix products (A10)

Apache Cassandra, ScyllaDB, Amazon Keyspaces

## R1 catalog of the domain

Domain: database. Catalog: `R1_CATALOG` of `e2e_usecases_w.py` (VM, ŞE, EY, OY, TA, DA, YD, AO), accepted by the owner on 2026-10-29. The page shows it under the R1–R5 callout with a Keyspaces example per code.

## Use cases (M2): candidates, weights, results (model 2)

| No | Use case | Candidates (best fit first) | R1 sub-items (codes) | R1 weight | Totals /100 | sim |
|---|---|---|---|---|---|---|
| 1 | Activity history per user (Lale Market) | Keyspaces, DynamoDB, Aurora | EY, OY, YD, DA | 50 | 97.8 / 90.6 / 66.8 (R1 50 / 47.6 / 37.6) | |
| 2 | Time-ordered sensor readings (wind farm) | Keyspaces, Timestream for InfluxDB, DynamoDB | EY, VM, DA, YD | 50 | 91.2 / 88.4 / 85.2 (close race; InfluxDB wins R1 50 vs 42) | w_sensor |
| 3 | Messaging inbox (support chats) | **DynamoDB**, Keyspaces, Aurora | EY, OY, YD, AO | 44 | 98 / 80.2 / 76.6 | |
| 4 | Audit logs | Keyspaces, DynamoDB, Aurora | EY, TA, AO, OY | 46 | 92.2 / 88 / 78.2 (close race; Aurora wins R1 45.2) | |
| 5 | Shopping cart in a Cassandra shop | Keyspaces, DynamoDB, MemoryDB | TA, EY, YD | 38 (R4 28; note says why) | 93.4 / 78.4 / 73.4 | |
| 6 | Device state with TTL (thermostats) | **DynamoDB**, Keyspaces, ElastiCache | EY, OY, YD | 42 | 95 / 86.4 / 80.2 (Keyspaces wins R1 42 vs 38.4) | |
| 7 | Click streams: continue where you left | Keyspaces, DynamoDB, Redshift | EY, DA, OY, YD | 46 | 77 / 76.6 / 62 (close race, gap 0.4) | w_clicks |
| 8 | Fraud signals per account | **DynamoDB**, Keyspaces, MemoryDB | EY, DA, YD, OY | 42 | 98.8 / 88.2 / 75.8 (R1 equal 40.8 / 40.8) | w_fraud |
| 9 | Product reviews per product | **Aurora**, DocumentDB, Keyspaces | EY, AO, OY, TA | 52 | 95.6 / 77 / 55.6 (Keyspaces third, R1 16.6 of 52) | w_reviews |
| 10 | Migration of an on-premises Cassandra | Keyspaces, DynamoDB, Apache Cassandra on EC2 (twin) | ŞE, EY, TA, YD | 46 | 95 / 74.8 / 74.4 (twin R1 43.8, third on R4) | w_migration |

Simulations (chosen after scoring): w_migration (Keyspaces wins on its engine features, R1 46/46, against its twin), w_sensor (another engine wins R1 and is third), w_clicks (close race, gap 1.6, "both together"), w_fraud (R1 equal, service design decides), w_reviews (clear loss, Keyspaces third).

- Keyspaces clearly loses: card 9 (Aurora, gap 40 to Keyspaces, R1 16.6 of 52), card 3 (DynamoDB, gap 17.8), card 6 (DynamoDB, gap 8.6), card 8 (DynamoDB, gap 10.6).
- Another engine wins R1 but loses on the total: card 2 (InfluxDB 50 vs Keyspaces 42), card 4 (Aurora 45.2 vs 38.2). Inverse: card 6 (Keyspaces wins R1, DynamoDB wins the total).
- R1 equal and service design decides: card 8 (DynamoDB vs Keyspaces 40.8 / 40.8); near equal in cards 1 and 7.
- Twin: Apache Cassandra on EC2 in card 10, third behind DynamoDB because of R4 (R1 43.8 vs 46: Keyspaces is a different engine with the same API, so not exactly equal; Paxos cost of LWT and tombstone compaction). Card 5 says why the twin is not a candidate (the operator leaves).
- "Both together": card 7 (Keyspaces for the strip, CDC → S3 → Redshift for the weekly report), card 2 (InfluxDB next to Keyspaces if live windows are wanted), card 8 (MemoryDB for the last days next to DynamoDB if the budget were 1 ms), card 6 (ElastiCache as a cache in front of DynamoDB).

Services checked and left out: Timestream for LiveAnalytics (closed to new customers since 2025-06-20), ElastiCache in cards 5 and 8 (loss of a cart/signal is not accepted; MemoryDB is the durable twin), OpenSearch and S3 + Athena for audit logs (not a system of record / no point lookups in seconds), Neptune (no relations).

Rules made explicit after the reader simulation (2026-10-31, docs/keyspaces.reader-report.md): pre-warming / instance class / node count = R4, meeting a (sudden) peak = R2; R5 scores only the price model, extra writes caused by the engine model are counted in R1 only; converting existing code to another API = R4, never R1; a missing change stream is counted in R1 · YD only, the Lambda trigger in R4 only. Consistency rules applied across the cards (and with the DynamoDB page): Keyspaces CDC exists = R1 · YD full; that it does not trigger a Lambda = R4 (5 off with "team does not know CQL", 6 off when Lambda connection pooling is also needed; DynamoDB page IoT card: 5); TTL filtered on read = YD 10 for Keyspaces, DynamoDB "within a few days" = YD 8 when a screen must hide expired data, 9 when it is harmless; TTL delete billing = R5 1–2 off; first big peak needs warm throughput = R2 1 off for both serverless services; rewriting existing CQL code = R4 (card 1: 4 off, card 5: 7 off, card 10: 8 off by size of the code); Keyspaces has no index = AO; clustering column cannot change = OY.

## New facts used in model 2 (with source)

| Claim | Source |
|---|---|
| Reads LOCAL_ONE or LOCAL_QUORUM, all writes LOCAL_QUORUM, RF 3 over several AZs | https://aws.amazon.com/keyspaces/pricing/, https://docs.aws.amazon.com/keyspaces/latest/devguide/consistency.html |
| No CREATE INDEX, materialized view, aggregate functions, UDF, TRUNCATE; "Security settings: Replaced by IAM"; compaction/compression "Not applicable" | https://docs.aws.amazon.com/keyspaces/latest/devguide/cassandra-apis.html |
| IAM cassandra:Modify "Grants permission to INSERT, UPDATE or DELETE data in a table" | https://docs.aws.amazon.com/service-authorization/latest/reference/list_keyspaces.html |
| CDC streams consumed with the Keyspaces Streams API or the KCL (Keyspaces Streams Kinesis adapter) | https://docs.aws.amazon.com/keyspaces/latest/devguide/cdc_how-to-use-kcl.html |
| Expired TTL data not returned in queries, removed "typically within 10 days", counts toward storage until removed | https://aws.amazon.com/blogs/database/announcing-amazon-keyspaces-time-to-live-ttl-general-availability/ |
| PITR any second in the preceding 35 days | https://aws.amazon.com/keyspaces/pricing/ |
| Per partition 3,000 RCU / 1,000 WCU; sustained hot partitions may be split | https://docs.aws.amazon.com/keyspaces/latest/devguide/bp-partition-key-design.html |
| Timestream for InfluxDB: instance classes medium–24xlarge, storage 20–15,360 GiB, 3,000/12,000/16,000 IOPS storage, SINGLE_AZ or WITH_MULTIAZ_STANDBY | https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_UpdateDbInstance.html |
| Timestream for LiveAnalytics closed to new customers (2025-06-20) | https://docs.aws.amazon.com/timestream/latest/developerguide/AmazonTimestreamForLiveAnalytics-availability-change.html |
| MemoryDB: microsecond reads, single-digit ms writes, Multi-AZ transactional log | https://docs.aws.amazon.com/memorydb/latest/devguide/servicename-feature-overview.html |

The model 1 facts (LWT no extra charge, Paxos cost in Cassandra, TTL delete per KB, CDC 24 h and view types, row 1 MB, 3,000 CQL queries per connection, on-demand to previous peak, multi-Region lag) keep their sources in the page and in the comment block above `KS_USECASES`.

## Known traps (handled explicitly in Part A)

1. Query without the partition key is not allowed → A5 read paths table ("Reddeder", ALLOW FILTERING), flow pair, two "Aklına şu gelebilir" boxes; B2 live refusal.
2. Tombstones → A6 concept card and "tombstone sources" table, ask box; A7 lifecycle; B3 delete table; M2 cards 3 and 9.
3. LWT cost → A6 concept card (Paxos in Cassandra, no extra charge in Keyspaces, failed condition billed), ask box; B3 code and `lwt` simulation.
4. Consistency levels → A4 concept card and all-cases table (with the levels Keyspaces lacks); B2 live LOCAL_ONE and `consistency` simulation; checkpoint.
5. CQL learning → A1 ask, A2 ask ("relational table değil mi"), M3 row, M4 last question; R4 in every card.
6. Upsert (added) → A3 2×2 table, A6 concept card and checkpoint.

## Live artifacts

| Structure | Artifact | How to take it |
|---|---|---|
| partition, rows | C00005, 10 rows newest first | `/keyspaces/api/e2e/K1` (B1) |
| clustering range | empty slice, 20 ms | `/keyspaces/api/e2e/K2` (B2) |
| partition size | 942 rows | `/keyspaces/api/e2e/K3` (B4) |
| refused query | ALLOW FILTERING error | `/keyspaces/api/e2e/K4` (B2) |
| LOCAL_ONE read | same 10 rows | `/keyspaces/api/e2e/K5` (B2) |
| schema roles | system_schema.columns | `/keyspaces/api/e2e/K6` (B1) |
| table settings | TTL, PITR, on-demand, warm throughput | `/keyspaces/api/e2e/K7` (B5); `aws keyspaces get-table` (C3) |

The live table still had seed data (written 2026-10-26, TTL 7 days); no rows were created. Model 2 regeneration (2026-10-30): no new live reads or writes; the artifacts above (taken 2026-10-29) are reused unchanged. The seed rows expire by TTL around 2026-11-02; the page says so in B5.

## Teaching data

`ACT` in `e2e_sims.py`: 8 rows in 3 partitions (C00005 four rows, C00001 two, C00006 two), rendered with `k.sample("activity")` in A3; the teaching token is the customer number modulo 3 (A4 diagram and the `partition` simulation use the same `_token`).
