# Scope: Aurora PostgreSQL (aurora)

status: pilot
domain-map row: verified
date: 2026-10-29

Page: `app/engine_app/templates/e2e/aurora.tr.html` (Turkish only; the old English `aurora.html` stays untouched). Data: `AURORA_USECASES` in `app/engine_app/e2e_usecases.py`. Simulations: the Aurora section of `app/engine_app/e2e_sims.py` (five `usecase_scorecard` decisions from the cards plus the nine mechanism simulations).

## Part A topic and the everyday picture (A1)

- Category in one general term: the relational database (tables, rows, keys, SQL, transactions)
- Everyday picture: a bookshop with three cashiers and one shared spreadsheet file; the database is the single clerk behind the counter
- The trade (what it gives, what it takes): every fact once and tables linked by keys / a screen joins several tables at query time; a question on any column without redesign / the planner decides the path, a wrong plan is a slow query; rules in the database, applied on every write / rules are written up front, a new column is a schema change; several writes in several tables all-or-nothing, the second writer waits / all writes go through one writer

## Feature list Ö1–Ö8 (F1–F8 of the domain map)

| No | Feature | Defining section | Official sentence (URL) | Limit |
|---|---|---|---|---|
| Ö1 | Schema with types and constraints | A2 | "a check constraint is satisfied if the check expression evaluates to true or the null value" (https://www.postgresql.org/docs/current/ddl-constraints.html) | rules are written up front; a frequently changing shape needs JSONB or a migration |
| Ö2 | Primary and foreign keys (relations) | A3 | "Adding a primary key will automatically create a unique B-tree index" (same URL) | no relation means pure overhead; many-to-many needs a link table |
| Ö3 | SQL on any column, JOIN, GROUP BY | A4 | PostgreSQL SQL tutorial (https://www.postgresql.org/docs/current/tutorial-sql.html) | full scans run on one server and read whole rows; no typo-tolerant relevance search |
| Ö4 | Indexes chosen by a planner | A5 | B-tree default, EXPLAIN (https://www.postgresql.org/docs/current/indexes-types.html, https://www.postgresql.org/docs/current/using-explain.html) | every index costs on every write; the planner may skip an index (function, '%x%', non-selective) |
| Ö5 | Transactions and row locks (ACID) | A6 | Read Committed default, UPDATE re-evaluates the WHERE on the new row version, Serializable needs retries (https://www.postgresql.org/docs/current/transaction-iso.html) | one writer; a hot row becomes a queue; long transactions keep locks and dead tuples |
| Ö6 | Views and functions (triggers) | A7 | PostgreSQL views and triggers (https://www.postgresql.org/docs/current/sql-createview.html) | not a workflow engine; trigger code needs versioning and tests |
| Ö7 | Replication and failover | A8 | six storage nodes in three AZs, up to 15 Aurora Replicas, failover "typically restored in less than 60 seconds, and often less than 30 seconds", replica lag "usually considerably less than 100 milliseconds" (https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html, https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Performance.html) | the writer is single; write volume beyond one writer needs sharding (Limitless) or another model |
| Ö8 | Extensions (JSONB, PostGIS, pgvector) and row-level security | A9 | RLS definition and bypass by superusers and owners (https://www.postgresql.org/docs/current/ddl-rowsecurity.html); Aurora PostgreSQL 17.9 extension versions, PostGIS 3.5.1, pgvector 0.8.1 (https://docs.aws.amazon.com/AmazonRDS/latest/AuroraPostgreSQLReleaseNotes/AuroraPostgreSQL.Extensions.html) | no foreign key inside JSONB; only the supported extension list; policies need per-role tests |

## All cases per concept

| Section | Concept | Cases (including the impossible one) |
|---|---|---|
| A2 | value written into a column | fits the type; wrong type (refused); NULL allowed; NOT NULL (refused); CHECK broken (refused, CHECK accepts NULL); DEFAULT; column not in the schema (cannot) |
| A2 | schema change | add column; drop column; change type; add rule with an existing violating row (refused); drop a table that is referenced (refused) |
| A3 | two rows, primary key and foreign key | same primary key (no); different / same foreign key (group); different / different; foreign key without owner (no); NULL foreign key |
| A3 | owner row deleted | RESTRICT (refused); CASCADE; SET NULL; no foreign key (no check) |
| A4 | a question and its SQL | by primary key; any column; range, pattern, list; JOIN; LEFT JOIN; GROUP BY; HAVING; ORDER BY LIMIT; information not in the schema (cannot); typo-tolerant ranked search (cannot at scale) |
| A4 | JOIN matching | owner exists; owner with many borrowers; owner without borrowers; join without condition (cross product); many-to-many needs a link table |
| A5 | a condition and the planner | primary key equality; indexed range; prefix LIKE; '%x%' (index unusable); function on column (index unusable); no index; non-selective condition (seq scan); tiny table |
| A6 | how a transaction ends | COMMIT; ROLLBACK; crash before COMMIT; error inside (aborted state); undo after COMMIT (cannot); long open transaction |
| A6 | two sessions on one row | read/read; write/read (MVCC); write/write (lock wait, re-test); read then write both (lost update); opposite order (deadlock); SELECT FOR UPDATE |
| A7 | forms of a view | plain view read; materialized read; refresh; write into a view (cannot in general); drop a column used by a view (refused) |
| A7 | where logic lives | constraint; trigger or application transaction; view; materialized view; workflow (not the database's job) |
| A8 | failure and copies | reader down; writer down (failover); AZ down; Region down; replica lag; second writer (cannot); wrong DELETE committed (copy is not a backup) |
| A9 | shape and place of data | fixed columns; JSONB; JSONB with GIN; foreign key inside JSONB (cannot); PostGIS; pgvector; row-level security; large files (not in the database) |
| C2 | which job to which endpoint | writes (cluster); read-your-own-write (cluster); reports (reader); failover with an open connection |

## Anatomy list and colors

- Core data structures: table, row, column, primary key, foreign key, index, transaction (and in Part B: page, tuple)
- Colors: primary key yellow (`c-pk`), foreign key blue (`c-sk`), other columns grey; stated in the A3 anatomy caption; `k.sample(..., pk=, sk=)` and the anatomy diagrams of A3 and B1 use the same colors

## Matrix products (A10)

PostgreSQL (community), MySQL, Aurora PostgreSQL

## Use cases (M2) and their closest alternatives

| No | Use case | Alternative 1 | Alternative 2 | sim (win / lose / race / none) | Totals |
|---|---|---|---|---|---|
| 1 | Checkout: order, stock, payment (Lale Market) | DynamoDB | DocumentDB | win_checkout | Aurora 47, DynamoDB 41, DocumentDB 35 |
| 2 | Product catalog with relations (JSONB attributes) | DocumentDB | OpenSearch | race_catalog | Aurora 44, DocumentDB 42, OpenSearch 32 |
| 3 | Warehouse stock with reservations | DynamoDB | ElastiCache | none | Aurora 44, DynamoDB 43, ElastiCache 35 |
| 4 | Customer accounts, addresses, consents | DynamoDB | DocumentDB | none | Aurora 45, DynamoDB 43, DocumentDB 41 |
| 5 | Multi-tenant SaaS with row-level security | RDS for PostgreSQL | DynamoDB | none | Aurora 46, RDS 42, DynamoDB 39 |
| 6 | Reporting: from 90 days to three years of history | Redshift | OpenSearch | lose_reporting | Redshift 45, Aurora 32, OpenSearch 31 |
| 7 | Invoices and double-entry ledger | RDS for PostgreSQL | DynamoDB | race_ledger | Aurora 45, RDS 43, DynamoDB 39 |
| 8 | Appointments: non-overlapping time ranges | DynamoDB | ElastiCache | race_booking | Aurora 44, DynamoDB 43, ElastiCache 34 |
| 9 | Workflow state with audit trail | DynamoDB | DocumentDB | none | Aurora 47, DynamoDB 44, DocumentDB 41 |
| 10 | Geospatial: delivery zones and nearest points (PostGIS) | OpenSearch | DynamoDB | none | Aurora 45, DynamoDB 38, OpenSearch 35 |

Aurora loses card 6 (Redshift). "Both together" is the honest answer in card 6 (Aurora as system of record, zero-ETL to Redshift) and in card 2 (Aurora for the catalog, OpenSearch for search). New entries added to the shared parts: `CATEGORY["rds"]`, `LINK["rds"]` (additions only; `SVC` already had `rds`). The `usecase()` assert now accepts any chosen service that is in `CATEGORY` (the DynamoDB cards still pass `ddb`).

## Known traps (handled explicitly in Part A)

1. One writer → A8 concept "Replica", the "second writer: cannot" row, the "You may ask" box on why writes do not scale with replicas; M3 first row.
2. MVCC and dead rows (vacuum) → A6 "Row lock" card (MVCC), the "long open transaction" row; B1 "Tuple" card; B6 vacuum row and checkpoint.
3. A lost update without a lock → A6 two flow diagrams and the "read then write" row of the two-session table; B5 `lost` and `locked` simulations.
4. An index that the planner does not use → A5 all-cases table ('%x%', function on column, non-selective condition, tiny table) and the "You may ask" box; B2 live plans.
5. ACU minimum cost → M5 Serverless v2 row (0.5–256 ACU, 0 with auto-pause on supported versions), B6 cost table; every card's R5 reason names the minimum capacity.

## Live artifacts

| Structure | Artifact | How to take it |
|---|---|---|
| row | `SELECT * FROM customers WHERE customer_id = 'C00001'` | live site `/aurora/api/e2e/A2` (B1) |
| table sizes | row counts of the four tables (1000, 200, 5007, 12519) | `/aurora/api/e2e/A1` (B1) |
| JOIN result | O000001 with customer and product names, 4 rows | `/aurora/api/e2e/A3` (B3) |
| GROUP BY result | revenue per category over 12,519 lines | `/aurora/api/e2e/A4` (B3) |
| indexes | `pg_indexes` of the public schema | `/aurora/api/e2e/A5` (B1) |
| query plans | Index Scan (shared hit=3) and Seq Scan (shared hit=20, 999 rows removed) | `/aurora/api/e2e/A6`, `A7` (B2) |
| refused writes | foreign key violation and check violation messages | `/aurora/api/e2e/A8`, `A9` (B4) |
| conditional UPDATE | `RETURNING stock_after = 123`, then ROLLBACK | `/aurora/api/e2e/A10` (B5) |
| cluster | engine 17.9, Serverless v2 0.5–4 ACU, writer in eu-central-1a, reader in 1b, three AZs, endpoints | `aws rds describe-db-clusters` (C3) |

## Teaching data

The four tables of `e2e_sims.py` (`CUSTOMERS` 6 rows, `PRODUCTS` 5 rows, `ORDERS` 4 rows, `ITEMS` 9 rows), rendered with `k.sample` in A2 and A3; names and prices come from the real Lale Market data, stock values and the orders after O000001 are examples.
