# Scope: Amazon ElastiCache (Valkey) (elasticache)

status: pilot
domain-map row: verified
date: 2026-10-29

Page: `app/engine_app/templates/e2e/elasticache.tr.html` (Turkish only; the old English `elasticache.html` stays untouched). Data: `EC_USECASES` in `app/engine_app/e2e_usecases.py`. Simulations: the ElastiCache section of `app/engine_app/e2e_sims.py` (five `usecase_scorecard` decisions from the cards, the mechanism simulations `race_naive`, `race_atomic`, `zset`, `cache`, and the new `slots` and `failover`; the three legacy `decide_*` 2/1/0 decisions stay in `_ec_legacy()` only for the old English page).

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

## Use cases (M2) and their closest alternatives

| No | Use case | Alternative 1 | Alternative 2 | sim | Totals |
|---|---|---|---|---|---|
| 1 | Sessions and login tokens | DynamoDB | MemoryDB | race_session | ElastiCache 43, DynamoDB 42, MemoryDB 40 |
| 2 | Live leaderboards (Lale Market) | MemoryDB | DynamoDB | race_board | ElastiCache 45, MemoryDB 42, DynamoDB 38 |
| 3 | Rate limits and counters | MemoryDB | DynamoDB | win_rate | ElastiCache 46, MemoryDB 39, DynamoDB 38 |
| 4 | Cache-aside for the product page (Lale Market) | Aurora | DynamoDB | none | ElastiCache 45, Aurora 39, DynamoDB 39 |
| 5 | Real-time counters: views and unique visitors | DynamoDB | Timestream for InfluxDB | none | ElastiCache 43, DynamoDB 37, Timestream for InfluxDB 34 |
| 6 | Pub/Sub for live updates | DynamoDB (Streams) | MemoryDB | none | ElastiCache 43, DynamoDB 39, MemoryDB 37 |
| 7 | Distributed lock: seller payout runs exactly once | DynamoDB | MemoryDB | lose_lock | DynamoDB 48, MemoryDB 38, ElastiCache disqualified on R3 (38) |
| 8 | Job queue with lists: image thumbnails | MemoryDB | DynamoDB | none | ElastiCache 40, MemoryDB 38, DynamoDB 37 |
| 9 | Recommendation cache | DynamoDB | Aurora | race_reco | DynamoDB 44, ElastiCache 43, Aurora 32 |
| 10 | Nearby couriers: geospatial lookups | Aurora (PostGIS) | OpenSearch | none | ElastiCache 43, Aurora 38, OpenSearch 35 |

ElastiCache loses card 7 (durability-critical lock, R3 must, 1 point on R3, disqualified; DynamoDB wins clearly) and card 9 (by one point; "both together": durable list in DynamoDB, hot read in ElastiCache). "Both together" is also the answer in card 4 (ElastiCache in front of Aurora) and card 10 (live positions in ElastiCache, zones and prices in Aurora). Card 8 names Amazon SQS as the usual answer when the jobs must not be lost (no SQS page yet, so SQS is not a scored candidate).

Consistency with the DynamoDB page: the ElastiCache and DynamoDB scores of cards 1, 3 and 9 are the same as the DynamoDB cards `session` (43/42), `rate` (46/38) and `ads` (44/43); only the third candidate differs. Shared parts: additions only (`CATEGORY["mdb"]`, `LINK["mdb"] = "elasticache"`; `SVC` already had `mdb`; `COUNT_TR` got two counter names).

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
