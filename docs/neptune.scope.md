# Scope: Amazon Neptune (neptune)

status: verified (database domain, model 2)
domain-map row: verified (Neptune row of references/domain-map.md), refined here
date: 2026-10-31

Page: `app/engine_app/templates/e2e/neptune.tr.html` (Turkish only; replaces the older Turkish page). The old English
`neptune.html` stays untouched and keeps its legacy simulations (`decide_recs`, `decide_report`, `hop2`, `hop3`, `path`).
Cards: `app/engine_app/e2e_usecases_w.py` block `NEPTUNE_W`. Simulations: `app/engine_app/e2e_sims.py`, `neptune()`.

## Part A topic and the everyday picture (A1)

- Category: the property graph database (vertices, edges, traversal); RDF is the second form of the graph model.
- Everyday picture: a metro map. You put your finger on your station and follow the lines; you never read the list of all stations.
- The trade: the relation is stored as data and a query walks it hop by hop (cost = the neighbours, not the graph size);
  in return, questions over all records (sums, reports), free text and key-only lookups are weak, and a supernode is expensive.

## Twin decision

Neptune Database and Neptune Analytics share the property graph model and openCypher, but they are **not twins** in the sense of
decisions.md. Neptune Database is a cluster with a shared, six-copy cluster volume, three quad indexes (SPOG, POGS, GPSO) and OLTP
isolation (snapshot reads, READ COMMITTED mutations with range locks), built for queries that start at one vertex or a set of vertices.
Neptune Analytics is one memory-optimized instance with built-in graph algorithms (25+), a vector index (HNSW), snapshot reads for
mutations, and passive replicas. Their R1 differs (DA, AO, TA), so R1 is scored separately on every card. Neptune Serverless and
provisioned instances are the same Neptune Database engine (R2, R4, R5 only). Card SVC names: `np` "Neptune" (= Neptune Database),
`npa` "Neptune Analytics" (new entry).

## Feature list Ö1–Ö8

| No | Feature | Defining section | Official sentence (URL) | Limit |
|---|---|---|---|---|
| Ö1 | Property graph: vertex, edge, label, property (and RDF triples) | A2 | Neptune quads S, P, O, G; "A relationship between two vertices can be represented by storing the source vertex identifier in the S position, the target vertex identifier in the O position, and the edge label in the P position" (https://docs.aws.amazon.com/neptune/latest/userguide/feature-overview-data-model.html) | no schema, no constraints |
| Ö2 | Start point: ~id and property lookups by index | A3 | three default indexes SPOG, POGS, GPSO; OSGP only on an empty cluster (https://docs.aws.amazon.com/neptune/latest/userguide/feature-overview-storage-indexing.html) | no user-defined index; a query without a start reads all vertices |
| Ö3 | Traversal hop by hop (cost = neighbours) | A4 | Neptune is "optimized for transactional type queries that start at a single node or set of nodes and fan out" (https://docs.aws.amazon.com/prescriptive-guidance/latest/neptune-well-architected-framework/performance-efficiency-pillar.html) | supernodes |
| Ö4 | Pattern matching (openCypher, Gremlin, SPARQL) | A5 | Neptune supports openCypher, Gremlin and SPARQL (https://docs.aws.amazon.com/neptune/latest/userguide/feature-opencypher-compliance.html) | no CALL, no user-defined functions |
| Ö5 | Variable-length paths | A6 | VLP, each edge at most once per solution; shortestPath() and allShortestPaths() not supported (same URL) | unbounded depth is expensive |
| Ö6 | Transactions | A7 | read-only queries SNAPSHOT; mutations READ COMMITTED with range locks; lock wait up to 60 s (https://docs.aws.amazon.com/neptune/latest/userguide/transactions-neptune.html) | conflicts and retries; replica lag |
| Ö7 | Bulk load and change stream | A8 | bulk loader from S3 (https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load.html); Streams 1–90 days, default 7 (https://docs.aws.amazon.com/neptune/latest/userguide/streams-using-enabling.html) | no TTL (TTL with Lambda + DynamoDB: https://aws.amazon.com/blogs/database/implement-time-to-live-in-amazon-neptune-part-1-property-graph/) |
| Ö8 | Whole-graph algorithms and vector search | A9 | Neptune Analytics: 25+ algorithms as openCypher procedures, vector similarity search (https://docs.aws.amazon.com/neptune-analytics/latest/userguide/algorithms.html) | not in Neptune Database; one vector index per graph (https://aws.amazon.com/neptune/faqs/) |

## All cases per concept

| Section | Concept | Cases (including the impossible one) |
|---|---|---|
| A1 | Is the relation the data? | a value in a row (one join), a fixed chain (2–3 joins), unknown depth, the relation has properties, a sum over all records (graph is weak), free text (Cannot without OpenSearch) |
| A2 | Edge forms | directed, read in both directions, two edges between the same pair (multi-edge), self-loop, edge with properties, edge without its two vertices (Cannot) |
| A2 | Graph model forms | property graph (openCypher, Gremlin), RDF (SPARQL); one cluster can hold both, but a query language reads only its own model |
| A3 | Start point | by ~id, by label + property (POGS), by label only, by a property range, by nothing (all vertices), by text inside a property (Cannot without OpenSearch) |
| A4 | Traversal cost | small degree, two hops, supernode, vertex without edges, hop in the reverse direction, cost of the whole graph (no) |
| A5 | Pattern forms | one hop, two hops, condition on an edge property, NOT pattern, aggregation, pattern without a start (scan), CALL procedure (Cannot in Neptune Database) |
| A6 | Path forms | fixed length, range *1..6, unbounded *, cycles, shortest path (shortestPath() Cannot in Neptune openCypher; Gremlin or Neptune Analytics) |
| A7 | Write forms | CREATE vertex, CREATE edge, MERGE, SET property, DELETE edge, DELETE vertex with edges (Cannot, DETACH DELETE), bulk by pattern, multi-statement transaction, a constraint like UNIQUE (Cannot) |
| A8 | Life cycle | bulk load, change stream, expiry (Cannot: no TTL), backup and restore, copy to search |
| A9 | Local query vs whole-graph algorithm | one start, all vertices, PageRank, community, similarity, vector top-K, in Neptune Database (Cannot) |

## Anatomy list and colors

- Core data structures: vertex (~id, ~label, properties), edge (~id, ~from, ~to, ~label, properties), quad (S, P, O, G), path.
- Colors: yellow = the identifier a record or a query starts from (vertex ~id, edge ~from); blue = the second part (vertex ~label, edge ~to); grey = properties.

## Matrix products (A10)

Neo4j, JanusGraph (Apache TinkerPop), Amazon Neptune (Database / Analytics).

## R1 catalog of the domain

Domain: database. Catalog: simkit.R1_CATALOGS["database"] (VM, ŞE, EY, OY, TA, DA, YD, AO), unchanged.

## Use cases (M2): candidates, weights, results (model 2)

| No | Use case | Candidates (best fit first) | R1 sub-items | R1 weight | Totals /100 | sim |
|---|---|---|---|---|---|---|
| 1 | Social graph: people you may know | np, aur, ddb | EY DA OY VM | 50 | 90,5 / 80,4 / 73,8 | w_social |
| 2 | Fraud ring check at payment time | np, npa, aur | EY DA OY TA | 50 | 91,5 / 80,5 / 63,5 (R1 np = npa = 48,5) | w_fraud |
| 3 | Recommendations by graph (Lale Market) | np, aur, ddb | EY DA OY VM | 45 | 81 / 79 / 70 (close race) | w_reco |
| 4 | Product knowledge graph, GraphRAG | npa, os, np | EY DA VM AO | 50 | 87,5 / 77,5 / 73,5 | — |
| 5 | Identity graph | np, ddb, npa | EY OY DA TA | 50 | 87 / 83 / 77 (close race; R1 npa 47 > np 46) | — |
| 6 | Network topology, impact | aur, np, npa | EY DA VM OY | 45 | 86 / 75,5 / 71 (R1 np 44,5 > aur 31) | w_network |
| 7 | Supply chain risk, whole graph | npa, rs, np | EY DA AO VM | 45 | 87 / 67,5 / 63,5 | — |
| 8 | Access control, nested groups | np, ddb, aur | EY DA TA OY | 50 | 91,5 / 79 / 78,5 | — |
| 9 | Customer 360, call center | aur, doc, np | EY VM TA AO | 45 | 96,5 / 75,5 / 66 | w_c360 |
| 10 | Drug interactions, RDF/SPARQL | np, ddb, aur | VM EY ŞE AO | 50 | 94 / 70 / 67,5 | — |

- Neptune loses four cards: 4 and 7 to Neptune Analytics (vector search and algorithms are not in Neptune Database), 6 to Aurora
  (Neptune wins R1 by 13,5, Aurora wins on R4/R5: the data is already there and the traffic is tiny), 9 to Aurora clearly (one-hop
  relations, Neptune third).
- Another engine wins R1 but loses the total: card 5 (Neptune Analytics 47 vs Neptune 46 in R1, Neptune wins on R2/R5).
- Reader report (docs/neptune.reader-report.md, 30 findings) closed on 2026-10-31; the totals above are after the closure.
- R1 equal and service design decides: card 2 (Neptune vs Neptune Analytics).
- "Both together": card 2 (Neptune at payment, Neptune Analytics at night), card 3 (Aurora record, Neptune recommendation, cache),
  card 4 (catalog/Neptune Database record, Neptune Analytics retrieval), card 5 (Neptune Analytics nightly + DynamoDB lookup when
  people are computed in batch), card 7 (Neptune Database daily checks, Neptune Analytics weekly analysis), card 10 (Neptune ontology,
  DynamoDB expanded pairs at very high rates).
- Services checked and left out: ElastiCache (stores precomputed lists, cannot compute hops; its card 9 is the lookup of such lists),
  Keyspaces and Timestream (no relation queries), MemoryDB (same as ElastiCache), DocumentDB on graph cards ($graphLookup exists but
  is not the best fit anywhere a graph engine is a candidate; it is the candidate on card 9 where the data is a document).
- No workload of the accepted pages (DynamoDB, Aurora, DocumentDB, Keyspaces, ElastiCache) has Neptune as a candidate, so no points
  had to be copied. The closest workloads: DynamoDB "ads"/ElastiCache "reco" (lookup of precomputed lists, card 3 names them);
  Keyspaces "fraud" (fraud signals per account by key, card 2 is the multi-hop ring check).

## Known traps (handled explicitly in Part A)

1. "Customer 360 is a graph use case" -> A1 all-cases table (one hop is a join, no gain), card 9.
2. Supernode -> A4 concept card and all-cases table, cards 1, 2, 3, 5, 8.
3. Unbounded variable-length path and shortestPath() not supported in Neptune openCypher -> A6 Cannot row, B3.
4. No TTL, no schema constraints, no user-defined indexes -> A3, A7, A8 Cannot rows.
5. Neptune Database is not Neptune Analytics (algorithms, vectors) -> A9 table, M5, cards 4 and 7.
6. Retry duplicates edges with CREATE -> A7, B4 simulations (retry_create, retry_merge).

## Live artifacts

| Structure | Artifact | How to take it |
|---|---|---|
| vertex + edges | Customer C00001 with 92 outgoing BOUGHT edges (first 10), multi-edges to P0195 | GET /neptune/api/learn/item?id=C00001 (live site, 2026-10-31) |
| vertex + 2 hops | Product P0001: 73 incoming edges, bought together by count(*) (P0125: 42) | GET /neptune/api/learn/item?id=P0001 |
| query answer | Q1 for P0001 (count DISTINCT: P0041 10, ...), engine 205–273 ms; Q2 persona (P0063 71), 953 ms | GET /neptune/api/recs?product=P0001, ?mode=persona |
| graph size | 200 Product vertices, 11,887 BOUGHT edges | GET /neptune/api/learn/overview |
| cluster | dbws-neptune, engine 1.4.8.0, db.serverless writer (eu-central-1b) and reader (eu-central-1c), 1–8 NCU, IAM auth, backup 1 day | DescribeDBClusters / DescribeDBInstances (read only) |

## Teaching data

4 Customer vertices (C00001 Ayşe Yılmaz İstanbul, C00002 Mert Doğan Ankara, C00003 Elif Kaya İzmir, C00005 Zeynep Şahin İstanbul),
5 Product vertices (P0001, P0016, P0175, P0044, P0179), 10 BOUGHT edges e1–e10 with example order ids and quantities
(`e2e_sims.EXTRA_TABLES["np_bought"]`, `np_customers`, `np_products`). Names and products are real Lale Market records; the edges are examples.

## Prices used (Price List API, eu-central-1, 2026-10-31)

Neptune Serverless 0.1941 USD per NCU-hour (minimum 1 NCU per instance: about 142 USD per instance per month); storage 0.119 USD per
GB-month; 0.22 USD per million I/O; I/O-Optimized storage 0.267 USD per GB-month; db.t3.medium 0.115 USD per hour; Neptune Analytics
32 m-NCU 1.162 USD per hour, 128 m-NCU 4.647 USD per hour, a stopped graph 10 % of the price.

## Other facts and sources

- One primary and up to 15 replicas on the same cluster volume; failover "generally less than 30 seconds" (reliability pillar above);
  "typically restored in less than 120 seconds, and often less than 60 seconds" (https://docs.aws.amazon.com/neptune/latest/userguide/backup-restore-overview-fault-tolerance.html).
- Six copies of each 10 GB chunk in three AZs; backups up to 35 days; global database with up to five secondary Regions
  (https://aws.amazon.com/documentation-overview/neptune/, reliability pillar).
- Copies in three AZs, a replica connects to the existing volume (https://docs.aws.amazon.com/neptune/latest/userguide/storage.html).
- Query timeout `neptune_query_timeout`, per-query hint (https://docs.aws.amazon.com/neptune/latest/userguide/opencypher-query-hints-timeout-hint.html).
- Full-text search through Neptune-to-OpenSearch replication (https://docs.aws.amazon.com/neptune/latest/userguide/full-text-search.html).
- Neptune Analytics: one memory-optimized instance, replicas are passive failover targets, priced per m-NCU
  (https://docs.aws.amazon.com/prescriptive-guidance/latest/neptune-analytics-well-architected-framework/reliability-pillar.html);
  mutation reads under snapshot isolation (https://docs.aws.amazon.com/neptune-analytics/latest/userguide/query-isolation-level.html);
  Neptune Database vs Analytics (https://docs.aws.amazon.com/neptune-analytics/latest/userguide/neptune-analytics-vs-neptune-database.html).
- Redshift recursive CTE (https://docs.aws.amazon.com/redshift/latest/dg/r_WITH_clause.html).
