# Scope: Amazon Keyspaces (for Apache Cassandra) (keyspaces)

status: pilot
domain-map row: verified
date: 2026-10-29

Page: `app/engine_app/templates/e2e/keyspaces.tr.html` (Turkish only; the old English `keyspaces.html` stays untouched and keeps its legacy `decide_feed` / `decide_report` simulations). Data: `KS_USECASES` in `app/engine_app/e2e_usecases.py` (fact sources in the comment block above it). Simulations: the Keyspaces section of `app/engine_app/e2e_sims.py` (five `usecase_scorecard` decisions from the cards, the mechanism simulations `partition`, `nokey`, `consistency` and the new `lwt`).

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

## Use cases (M2) and their closest alternatives

| No | Use case | Alternative 1 | Alternative 2 | sim | Totals |
|---|---|---|---|---|---|
| 1 | Activity history per user (Lale Market) | DynamoDB | Aurora | race_activity | Keyspaces 44, DynamoDB 43, Aurora 34 |
| 2 | Time-ordered sensor readings | DynamoDB | Timestream for InfluxDB | race_sensor | Keyspaces 44, DynamoDB 43, InfluxDB 42 |
| 3 | Messaging inbox | DynamoDB | Aurora | none | DynamoDB 47, Keyspaces 41, Aurora 39 |
| 4 | Audit logs | DynamoDB | Aurora | none | Keyspaces 44, DynamoDB 42, Aurora 37 |
| 5 | Shopping cart in a Cassandra shop | DynamoDB | Aurora | none | Keyspaces 46, DynamoDB 41, Aurora 37 |
| 6 | Device state with TTL | DynamoDB | ElastiCache | lose_device | DynamoDB 47, Keyspaces 39, ElastiCache 38 |
| 7 | Click streams | DynamoDB | Redshift | none | Keyspaces 43, DynamoDB 41, Redshift 32 |
| 8 | Fraud signals per account | DynamoDB | ElastiCache | race_fraud | DynamoDB 45, Keyspaces 43, ElastiCache 35 |
| 9 | Product reviews per product | Aurora | DocumentDB | none | Aurora 45, DocumentDB 42, Keyspaces 37 |
| 10 | Migration of an on-premises Cassandra workload | Apache Cassandra on EC2 | DynamoDB | win_migration | Keyspaces 47, Apache Cassandra 37, DynamoDB 33 |

Keyspaces loses cards 3, 6, 8 (DynamoDB) and 9 (Aurora). "Both together" is the honest answer in card 7 (Keyspaces for the per-user strip, CDC to S3 and Redshift for the weekly report) and is named in card 8 (durable store plus ElastiCache for the hottest accounts). Consistency with the DynamoDB page: there Keyspaces loses sessions (41 vs 42) and IoT state (42 vs 48) because the team does not know CQL; here Keyspaces wins only where CQL knowledge or Cassandra code exists (cards 1, 2, 4, 5, 7, 10) and loses where the team knows DynamoDB (3, 6, 8).

Shared parts, additions only: `CATEGORY["cas"]`, `LINK["cas"]` (e2e_usecases.py), `SVC["cas"] = "Apache Cassandra"` (e2e_sims.py). No change to `ui.yaml`, CSS, JS, `images.yaml` (the three existing Keyspaces images are reused).

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

The live table still had seed data (written 2026-10-26, TTL 7 days); no rows were created.

## Teaching data

`ACT` in `e2e_sims.py`: 8 rows in 3 partitions (C00005 four rows, C00001 two, C00006 two), rendered with `k.sample("activity")` in A3; the teaching token is the customer number modulo 3 (A4 diagram and the `partition` simulation use the same `_token`).
