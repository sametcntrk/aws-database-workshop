# Scope: Amazon DynamoDB (dynamodb), Turkish page, weighted model (model 2) pilot

status: pilot of model 2 (weighted R1 "Engine uyumu")
date: 2026-10-29

Page: `app/engine_app/templates/e2e/dynamodb.tr.html`. Data: `DDB_W` in `app/engine_app/e2e_usecases_w.py` (model 2).
Simulations: `weighted_scorecard()` in `app/engine_app/e2e_sims.py` (Turkish only: `w_iot`, `w_cart`, `w_seat`, `w_session`, `w_rate`).
Card macro: `wusecase` in `templates/e2e/_macros.html`. Check: `~/.claude/skills/e2e-tech-tutorial/scripts/check_usecases.py --app app dynamodb` (model 2).

Untouched: the English page `dynamodb.html` (model 1 data `DDB_USECASES` + `e2e_usecases_en.py`, sims `race_*`, `win_iot`, `lose_rate`), and the Turkish pages of Aurora, Keyspaces, DocumentDB and ElastiCache (model 1). Their rendered HTML equals `main` except the UI label dictionary, which has new keys.

## Decisions of the owner (grill, 2026-10-29)

- R1 is renamed "Engine uyumu: veri, erişim ve garanti modeli" and scores only the nature of the engine (working principle, algorithm, tools). AWS packaging (serverless, Multi-AZ, pricing) goes to R3–R5. Candidates stay AWS services.
- R1 is split into 3–5 sub-items per card, from a fixed catalog of the database domain: VM, ŞE, EY, OY, TA, DA, YD, AO. In a card they are numbered R1.1 … R1.n and carry the code.
- Weights per card from the priorities of the workload, sum 100, set before the scores, one reason per row; R2–R5 at least 5; R1 split over its sub-items. R3–R5 lighter than R1 (vendor design decisions) but never removed.
- No must rows and no disqualification.
- The best fit (the highest total) is on top of the card; the page's service stays in the table with a badge. The candidates are the services that really fit the workload, so the best fit is always among them.
- M7 simulations replay the card data row by row. No 1 win / 1 loss / 3 races rule; "yakın yarış" (gap ≤ 5) is information only.
- R1–R5 table has a "Kaynağı" column (engine's nature / vendor's service design), with a callout on why.

## Candidate changes against model 1

| No | Card | Model 1 candidates | Model 2 candidates (best fit first) | Why |
|---|---|---|---|---|
| 3 | Sessions | DynamoDB, ElastiCache, Keyspaces | ElastiCache, MemoryDB, DynamoDB | Keyspaces does not fit sessions; MemoryDB is the real alternative (same engine, durable) |
| 4 | Game inventory | DynamoDB, DocumentDB, ElastiCache | DynamoDB, DocumentDB, Aurora | a purchased item must not be lost; ElastiCache Serverless has no durable log |
| 6 | Idempotency keys | DynamoDB, ElastiCache, Aurora | DynamoDB, MemoryDB, Aurora | a lost key charges a card twice; MemoryDB is the durable Valkey option |
| 7 | Seat holds | DynamoDB, Aurora, ElastiCache | DynamoDB, MemoryDB, Aurora | same reason as card 6 |
| 8 | Rate limits | DynamoDB, ElastiCache, Aurora | ElastiCache, MemoryDB, DynamoDB | Aurora does not fit a 2 ms counter |
| 10 | Recommendation lists | DynamoDB, ElastiCache, Aurora | ElastiCache, MemoryDB, DynamoDB | Aurora does not fit 100,000 reads/s under 5 ms |

## Results (weighted totals out of 100, after the reader simulation)

| No | Card | R1 weight | Totals | Best fit | sim |
|---|---|---|---|---|---|
| 1 | Cart | 50 | DynamoDB 93.3, ElastiCache 81.9, Aurora 77 | DynamoDB | w_cart |
| 2 | Profiles | 50 | DynamoDB 95.5, DocumentDB 86.8, Aurora 73.3 | DynamoDB (DocumentDB wins R1 by 4.5) | |
| 3 | Sessions | 55 | ElastiCache 95, MemoryDB 85, DynamoDB 76.5 | ElastiCache | w_session |
| 4 | Game inventory | 45 | DynamoDB 91.8, DocumentDB 77.5, Aurora 67.5 | DynamoDB | |
| 5 | IoT last state | 45 | DynamoDB 99, Keyspaces 94, InfluxDB 53 | DynamoDB (race, gap 5; R1 equal with Keyspaces) | w_iot |
| 6 | Idempotency keys | 50 | DynamoDB 96.5, MemoryDB 90.8, Aurora 88.7 | DynamoDB | |
| 7 | Seat holds | 50 | DynamoDB 89.5, MemoryDB 86.6, Aurora 77.5 | DynamoDB (race, gap 2.9; MemoryDB wins R1) | w_seat |
| 8 | Rate limits | 55 | ElastiCache 96, MemoryDB 82, DynamoDB 77 | ElastiCache | w_rate |
| 9 | File metadata | 45 | DynamoDB 96.5, DocumentDB 83, Aurora 77 | DynamoDB | |
| 10 | Recommendation lists | 50 | ElastiCache 86.5, MemoryDB 79.5, DynamoDB 79 | ElastiCache | |

## New facts used (with source)

| Claim | Source |
|---|---|
| DynamoDB TTL deletes expired items "typically within a few days"; use filter expressions to remove expired items from reads | https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html |
| `ReturnValuesOnConditionCheckFailure = ALL_OLD` returns the existing item in the failed conditional write | https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html |
| Warm throughput / pre-warming for planned peaks (10x, 100x) | https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/warm-throughput.html |
| MemoryDB: "microsecond read and single-digit millisecond write latency", Multi-AZ transactional log, strong consistency on primary, eventual on replicas | https://docs.aws.amazon.com/memorydb/latest/devguide/servicename-feature-overview.html |
| ElastiCache Serverless: ECPU = 1 per KB transferred for simple commands; minimum metered storage 100 MB for Valkey; doubles every 2–3 minutes, pre-scaling recommended for faster peaks | https://aws.amazon.com/elasticache/pricing/, https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Scaling-serverless.html |
| Keyspaces CDC streams: 24 h retention, read with the Keyspaces Streams API or KCL | https://docs.aws.amazon.com/keyspaces/latest/devguide/cdc.html |

Facts carried over from model 1 (400 KB item, 100-item transactions, Streams 24 h, zero-ETL to OpenSearch and Redshift) keep their sources in the page (M5, B sections).

## Open after acceptance

- Done 2026-10-29: model 2 rules, catalog questions, checker, macro and the example are in the skill.
- Regenerate the other Turkish pages (Aurora, Keyspaces, DocumentDB, ElastiCache) and wave 2 in model 2.
