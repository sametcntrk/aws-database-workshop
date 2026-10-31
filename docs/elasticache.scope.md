# Scope: Amazon ElastiCache (Valkey) (elasticache)

status: pilot
domain-map row: verified
date: 2026-10-29 (model 2 rebuild 2026-10-30)

Page: `app/engine_app/templates/e2e/elasticache.tr.html` (Turkish only; the old English `elasticache.html` stays untouched). Data: `ELASTICACHE_W` in `app/engine_app/e2e_usecases_w.py` (model 2; the model 1 `EC_USECASES` stays for the English page). Simulations: the ElastiCache section of `app/engine_app/e2e_sims.py` (five `weighted_scorecard` decisions from the cards, the mechanism simulations `race_naive`, `race_atomic`, `zset`, `cache`, and the new `slots` and `failover`; the three legacy `decide_*` 2/1/0 decisions stay in `_ec_legacy()` only for the old English page).

## Part A topic and the everyday picture (A1)

- Category in one general term: the in-memory key-value store (data structures, expiry)
- Everyday picture: the counter of a bakery (small, expensive, fast; emptied in the evening) in front of the stockroom (disk)
- The trade (what it gives, what it takes): microseconds / memory price per GB and the data must fit; data structures / a key is one part, no search inside the value; one atomic command / no rollback over several commands; exact expiry and eviction / a full memory deletes or refuses; speed / acknowledged writes can be lost (no durable log in Serverless)

## Feature list Ö1–Ö8 (F1–F8 of the domain map)

| No | Feature | Defining section | Official sentence (URL) | Limit |
|---|---|---|---|---|
| Ö1 | GET/SET from memory, microseconds | A1, A2 | "ElastiCache Serverless continuously monitors the memory, compute, and network bandwidth utilization of your cache" (https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.corecomponents.html) | memory price per GB-hour; "A value can't be bigger than 512 MB" (https://valkey.io/topics/strings/) |
| Ö2 | Data types (hash, list, set, sorted set, geo, HyperLogLog) | A3 | "A Sorted Set is a collection of unique strings (members) ordered by an associated score" and O(log(N)) adds (https://valkey.io/topics/sorted-sets/); HLL "uses up to 12 KB and provides a standard error of 0.81%" (https://valkey.io/topics/hyperloglogs/) | one score per sorted set; no nesting; polygon geo only with Valkey 9.0 (https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/SelectEngine.html) |
| Ö3 | Atomic commands (INCR, SET NX) and Lua | A5 | "a mostly single threaded design for command execution" (https://valkey.io/topics/latency/); "All the commands in a transaction are serialized and executed sequentially", "Valkey does not support rollbacks of transactions" (https://valkey.io/topics/transactions/) | no rollback; multi-key rules in one slot; atomic is not durable |
| Ö4 | Exact expiry (EXPIRE) and eviction | A6 | "The expire error is from 0 to 1 milliseconds" (https://valkey.io/commands/expire/); SET discards the TTL (https://valkey.io/commands/set/); eviction policies, noeviction "New values aren't saved when memory limit is reached" (https://valkey.io/topics/lru-cache/); volatile-lru default on node-based ElastiCache (https://aws.amazon.com/caching/best-practices/) | expiry per key (per-field only from Valkey 9.0); a full memory deletes or refuses; Serverless at a set maximum "will begin to evict data, to reject new writes with an Out of Memory error, or both" |
| Ö5 | Pub/Sub and streams | A8 | Pub/Sub at-most-once, "the message is lost" (https://valkey.io/topics/pubsub/); streams, consumer groups, XACK (https://valkey.io/topics/streams-intro/) | Pub/Sub never stored, also not in MemoryDB; streams and lists lost with the node when there is no durable log |
| Ö6 | Cluster mode: hash slots and shards | A4 | "HASH_SLOT = CRC16(key) mod 16384", hash tags, multi-key only in one slot (https://valkey.io/topics/cluster-spec/); CROSSSLOT (https://repost.aws/knowledge-center/elasticache-crossslot-keys-error-redis) | a hot key stays on one shard; 30K ECPU/s on an empty Serverless cache, doubling every 2–3 minutes, pre-scaling within 60 minutes (https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Scaling-serverless.html) |
| Ö7 | Replicas and failover | A9 | "Valkey Cluster uses asynchronous replication between nodes", "There is always a window of time when it is possible to lose writes during partitions" (cluster-spec); lock race on failover (https://valkey.io/topics/distlock/); Serverless "automatically replicates your data across multiple Availability Zones" and 99.99% SLA; node-based Valkey 9.0 durability: sync "designed for zero data loss at single-digit millisecond write latency", async "up to 10 seconds" (https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/durability.html); MemoryDB Multi-AZ transaction log (https://docs.aws.amazon.com/memorydb/latest/devguide/what-is-memorydb.html) | no durable log in Serverless; no point-in-time restore, only snapshots (daily, up to 35 days, https://aws.amazon.com/elasticache/faqs/) |
| Ö8 | Cache patterns (cache-aside, write-through) | A7 | caching best practices (https://aws.amazon.com/caching/best-practices/) | stale data up to the TTL; cold cache puts the whole load on the database; a copy is not a record |

## All cases per concept

| Section | Concept | Cases (including the impossible one) |
|---|---|---|
| A1 | can this data live only in memory | copy; derived; short-lived and harmless; short-lived but harmful (needs durable log); system of record (cannot) |
| A2 | forms of the key | one-part key; two-part key (none in Redis/Valkey); prefixes are conventions; read by part of a key (no cheap way, SCAN) |
| A2 | shape of the value | text/number; object; ordered structure; wrong-type command (WRONGTYPE); search inside the value (cannot); 512 MB limit |
| A3 | a question and its type | string, hash, list, set, sorted set, geo, HyperLogLog; several sort orders on one data (cannot with one type) |
| A4 | keys and slots | one-key command; multi-key same slot; multi-key different slots (CROSSSLOT); shard added; hot key; too wide hash tag |
| A5 | write paths | SET; INCR/DECR; SET NX/XX; read-then-write (not atomic); MULTI/EXEC; WATCH; Lua; rollback (cannot) |
| A6 | expiry | none; not yet; renewed; due; SET overwrites and discards TTL; HSET keeps TTL; per-field TTL (not in 8.1); deletion by the store |
| A6 | eviction policies | volatile-lru, allkeys-lru, LFU, volatile-ttl, random, noeviction; "never delete and never refuse" (cannot) |
| A7 | a read and the copy | hit; miss; stale; write-through; stampede; cold cache; copy as the only record (not a cache) |
| A8 | three messaging paths | who receives; nobody listening; reader crashed; replay (cannot in Pub/Sub); growth; store failure |
| A9 | what is lost in which failure | replica down; primary down after/before replication; AZ down; whole shard down; point-in-time restore (cannot) |
| B8 | defence against a lost lock | idempotent payout in DynamoDB; lock in DynamoDB; lock in MemoryDB/Valkey 9.0; WAIT (not a guarantee); ignore (not acceptable) |
| C2 | which job to which port | writes 6379; read-your-write 6379; stale-ok reads 6380; write to 6380 (refused); non-TLS client (cannot connect) |

## Anatomy list and colors

- Core data structures: key, value by type, member/field (with score), TTL, hash slot
- Colors: key yellow (`c-pk`), field or member blue (`c-sk`), value or score grey; stated in the A3 anatomy caption; B1 anatomy and the `valkey_slots` sample use the same colors

## Matrix products (A10)

Redis / Valkey (the Valkey engine of ElastiCache), Memcached, Amazon MemoryDB

## Use cases (M2), model 2 (weighted cards, 2026-10-30)

Data: `ELASTICACHE_W` at the end of `app/engine_app/e2e_usecases_w.py` (`USECASES_W["elasticache"]`, `PAGE_SVC["elasticache"] = "ec"`). Simulations: the five `w_*` of `e2e_sims.elasticache()` for `lang == "tr"` (`weighted_scorecard`). The model 1 `EC_USECASES` and the legacy sims stay for the untouched English `elasticache.html`.
Additions to shared tables (entries only): `SVC["sqs"] = "SQS"` (e2e_sims), `CATEGORY["sqs"]`, `LINK["sqs"] = "elasticache"` (SQS has no page; card 8 and M3 compare it); `SVC["sns"] = "SNS"`, `CATEGORY["sns"]`, `LINK["sns"] = "elasticache"` (card 6, after the reader simulation).

| No | Use case | R1 rows (weight) | Candidates, best first | Totals | R1 subtotals | sim |
|---|---|---|---|---|---|---|
| 1 | Sessions and login tokens | EY 10, YD 20, OY 10, DA 15 | ElastiCache, MemoryDB, DynamoDB | 95 / 85 / 76,5 | 55 / 55 / 35,5 | w_session (R1 equal, service decides) |
| 2 | Live leaderboards (Lale Market) | EY 20, OY 15, DA 10 | MemoryDB, ElastiCache, DynamoDB | 91 / 90 / 73,5 | 45 / 45 / 26,5 | w_board (Valkey engine features win; the twin wins the close race) |
| 3 | Rate limits and counters | OY 20, DA 15, YD 15, EY 5 | ElastiCache, MemoryDB, DynamoDB | 96 / 82 / 77 | 55 / 55 / 38 | – |
| 4 | Cache-aside for the product page | EY 15, TA 10, DA 15, YD 10 | ElastiCache, DynamoDB, Aurora | 94 / 83 / 74,5 | 48 / 41 / 42,5 | – (both together: ElastiCache in front of Aurora) |
| 5 | Real-time counters: views, unique visitors | OY 20, VM 10, EY 10, YD 10 | ElastiCache, DynamoDB, Timestream for InfluxDB | 90 / 68 / 64 | 48 / 34 / 34 | – (both together: live hour in ElastiCache, history in Redshift) |
| 6 | Pub/Sub for live updates | EY 20, DA 10, YD 10 | ElastiCache, MemoryDB, SNS | 95 / 81,5 / 78 | 40 / 40 / 35 | – (record in Aurora, notification in ElastiCache) |
| 7 | Distributed lock: seller payout once | TA 25, YD 10, OY 5, EY 5 | DynamoDB, MemoryDB, ElastiCache | 97 / 90 / 72 | 42 / 44 / 44 | w_lock (clear loss, decided by R3) |
| 8 | Job queue: image thumbnails | OY 15, TA 15, AO 10 | SQS, ElastiCache, MemoryDB | 97 / 81,5 / 77,5 | 38,5 / 31,5 / 31,5 | w_queue (loss decided by R1) |
| 9 | Recommendation cache | EY 10, DA 20, OY 15, VM 5 | ElastiCache, MemoryDB, DynamoDB | 86,5 / 79,5 / 79 | 48,5 / 48,5 / 40,5 | – |
| 10 | Nearby couriers: geo lookups | EY 15, YD 15, OY 10, DA 10 | ElastiCache, Aurora, OpenSearch | 87 / 77 / 64 | 41 / 44 / 36,5 | w_geo (Aurora wins R1, ElastiCache the total) |

ElastiCache is not the best fit in card 2 (its twin MemoryDB wins 91 to 90: small data, two small nodes cost about the same as Serverless, and the log prevents a 4-minute empty board), card 7 (DynamoDB; ElastiCache third, R3 1 point: an acknowledged lock can vanish in a failover) and card 8 (SQS; visibility timeout and dead-letter queue are engine tools of a queue, the Valkey stream keeps the delivery count, but reclaiming and dead-lettering are application code). "Both together" is the answer in cards 4, 5, 6 and 10. Another engine wins R1 but loses the total in card 10 (Aurora PostGIS 44 vs 41).

Twin rule: ElastiCache and MemoryDB have the same R1 points on all seven cards where MemoryDB is a candidate (1, 2, 3, 6, 7, 8, 9). Consistency with the DynamoDB page: cards 1, 3 and 9 are the workloads of the DynamoDB cards `session`, `rate` and `ads` with the same rows, weights and points (totals 95/85/76,5, 96/82/77, 86,5/79,5/79). The same mechanism gets the same reduction: ElastiCache R3 4 when the loss is accepted (no durable log in Serverless), 1 when the row wants "never lost" (card 7); MemoryDB R4 6 (no serverless option); MemoryDB R5 4-6 (node-hours); MemoryDB R2 only for the log commit where writes meet a latency limit (capacity configuration is R4, never R2).

Extra facts for the new cards (official sources):
- Prices, eu-central-1, AWS Price List API (2026-10-30): ElastiCache Serverless Valkey 0.101 USD per GB-hour and 0.0027 USD per million ECPU; MemoryDB Valkey db.t4g.small 0.0378 USD/h, db.r7g.large 0.2597 USD/h, data written free up to 10 TB/month (card 2, cards 3 and 9 R5 reasons).
- SNS: "published messages are stored across multiple, geographically-separated servers and data centers", delivery retry policy (https://aws.amazon.com/sns/features/).
- Global Datastore: up to two secondary Regions, typical replication under 1 second (https://aws.amazon.com/elasticache/faqs/, https://aws.amazon.com/elasticache/features/).
- Valkey streams: XAUTOCLAIM, XPENDING delivery count (https://valkey.io/commands/xautoclaim/, https://valkey.io/commands/xpending/).
- SQS standard queues: "at-least-once message delivery", "Amazon SQS redundantly stores the message in multiple availability zones (AZs) before acknowledging it" (https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html); long poll "a maximum of 20 seconds" (https://aws.amazon.com/sqs/faqs/); dead-letter queue after maxReceiveCount (https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html, https://repost.aws/knowledge-center/sqs-dead-letter-queue).
- ElastiCache Serverless supported commands: EVAL, SPUBLISH/SSUBSCRIBE, GEOSEARCH are supported; KEYS, FUNCTION/FCALL are unavailable on serverless caches (https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/SupportedCommands.html).
- MemoryDB: "designed as a primary database that combines in-memory speed with Multi-AZ durability" (https://aws.amazon.com/compare/msk-and-msk-serverless/ FAQ entry); node-based clusters (https://docs.aws.amazon.com/memorydb/latest/devguide/what-is-memorydb.html).

### Model 1 (kept for the English page)

The old model 1 totals (equal R1-R5, must rows) are in `EC_USECASES` and are no longer shown on the Turkish page.

## Known traps (handled explicitly in Part A)

1. No durable write log in Serverless → A1 trade table and "can this live only in memory" table, A9 concept "Kalıcı log" and the failure table, B8 `failover` simulation, card 7 (the clear loss), C2 comparison row "Kalıcı log: Yok".
2. Memory price per GB → A1 trade table and first "You may ask", M1 Ö1 limit, B9 cost table and the AWS blog example, R5 reasons of cards 9 and 2.
3. A key is one part → A2 title, concept card and "forms of the key" table (two-part key: none), the A2 checkpoint, the A3 "You may ask" about sort key versus score.
4. Eviction policies → A6 concept card and the policy table with the impossible row, the "Serverless at a maximum" "You may ask", B5.
5. A cold cache after failover → A7 table (cold cache row), A9 "You may ask" on cold cache, card 4 R3, B8 snapshot "You may ask".

## Live artifacts

| Structure | Artifact | How to take it |
|---|---|---|
| hash and string | `lm:deal` (5 fields) and `lm:deal:stock` = 46, with TYPE | live site `/elasticache/api/e2e/V1` (B1) |
| string with TTL | `lm:tut:greeting` merhaba, TTL 600 | `/elasticache/api/e2e/V2` (B2) |
| counter | INCR 1, 2, 3, INCRBY 10 = 13 | `/elasticache/api/e2e/V3` (B2) |
| hash field increment | P0001 = 3, P0044 = 1 | `/elasticache/api/e2e/V4` (B3) |
| sorted set | tutorial board, Elif at rank 5 | `/elasticache/api/e2e/V5` (B3) |
| TTL countdown | 5, 3, 1, -2 | `/elasticache/api/e2e/V6` (B5) |
| race | GET-then-SET sold 59 of 10, DECR sold 10 | `/elasticache/api/e2e/V7` (B2) |
| real leaderboard | top 5 of 994 members | `/elasticache/api/e2e/V8` (B3) |
| cache | dbws-cache, Valkey 8.1, ports 6379/6380, three subnets, SnapshotRetentionLimit 0 | `aws elasticache describe-serverless-caches --region eu-central-1` (C3) |

## Teaching data

`VKEYS` (five Lale Market keys, existing; the `zset` simulation now names its teaching key `lm:tut:board`, as in the live tutorial query V5) and the new `valkey_slots` table (six real keys with their real CRC16 slots: lm:deal 3299, lm:deal:stock 1725, lm:session:7f3a 9437, lm:session:3c8d 2435, lm:leaderboard 10162, lm:orders:today 15337; three teaching shards of 0–5460, 5461–10922, 10923–16383). The `slots` simulation and the A4 placement diagram use the same `_slot()` function (CRC16-XMODEM, checked against the known values foo = 12182 and user1 = 8106).

## Images

| File | Source | Licence | Used in |
|---|---|---|---|
| elasticache-memory-hierarchy.png | Wikimedia Commons | Public domain | A1 (Ö1) |
| elasticache-hash-table.png | Wikimedia Commons | CC BY-SA 3.0 | A2 (Ö1) |
| elasticache-node-groups.png (new) | AWS ElastiCache User Guide | AWS documentation | A4 (Ö6) |
| elasticache-shards-replicas.png (new) | AWS ElastiCache User Guide | AWS documentation | A9 (Ö7) |
| elasticache-serverless.png | AWS ElastiCache User Guide | AWS documentation | C2 |
| own drawings (anatomy, flows, parts) | page data | — | A3 (Ö2), A4, A5 (Ö3), A6 (Ö4), A7 (Ö8), A8 (Ö5), A9, B1 |
