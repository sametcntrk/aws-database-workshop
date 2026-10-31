# Scope: Amazon OpenSearch Service (opensearch)

status: verified (database domain, model 2)
domain-map row: verified (OpenSearch row of references/domain-map.md), extended here with Ö9 (vector search) and the twin OpenSearch Serverless
date: 2026-10-31

Page: `app/engine_app/templates/e2e/opensearch.tr.html` (Turkish only; replaces the older model 1 Turkish page).
Cards: `app/engine_app/e2e_usecases_w.py` (`OPENSEARCH_W`, `USECASES_W["opensearch"]`, `PAGE_SVC["opensearch"] = "os"`).
Simulations: `app/engine_app/e2e_sims.py` (`opensearch()`: five `w_*` from the cards plus `bm25`, `refresh`, `shards`, `geo_tr` for `lang == "tr"`;
the legacy `analyze`, `inverted`, `fuzzy`, `geo`, `decide_search`, `decide_orders` stay for the untouched English `opensearch.html`; the TR page reuses
`analyze`, `inverted` and `fuzzy`). The teaching copy `OS_DOCS` now holds the real P0175 ("Anadolu Yün Kazak 175"); the old copy had a name that is not in the live index.

## Part A topic and the everyday picture (A1)

- Category in one general term: the search engine (inverted index, analysis, relevance).
- Everyday picture: the index at the back of a book (word, then page numbers); a library card catalogue for documents and index.
- The trade: word search in any data size, typo and Turkish-letter tolerance, relevance, counts and geo in one request; in exchange no multi-document
  transaction, a write is searchable after a refresh, analysis is chosen up front (a change means a reindex), so the search engine is usually a copy of a system of record.

## Feature list Ö1–Ö9

| No | Feature | Defining section | Official sentence (URL) | Limit |
|---|---|---|---|---|
| Ö1 | Text analysis: analyzer and token | A3 | custom analyzers: char filters, tokenizer, token filters; asciifolding https://docs.opensearch.org/latest/analyzers/token-filters/asciifolding/ | an existing field's analyzer cannot change without a reindex |
| Ö2 | Inverted index and posting list | A4 | "OpenSearch uses a data structure called an inverted index" https://docs.opensearch.org/latest/getting-started/intro/ | infix search is not cheap; no JOIN |
| Ö3 | Relevance score (BM25) | A5 | BM25 default similarity (same intro page); live explain output (B3) | a score, not an exact order; tuning is work |
| Ö4 | Typo tolerance and prefix | A6 | fuzziness AUTO: 0–2 chars exact, 3–5 one edit, 6+ two edits https://docs.opensearch.org/latest/query-dsl/fuzziness/ | no tolerance for very short words |
| Ö5 | Aggregations | A7 | live O5 result (B4) | no JOIN; text fields are not aggregated; cardinality is approximate |
| Ö6 | Geo queries | A8 | geo_point / geo_shape, live O7 result (B5) | no road network; geometry validation narrower than PostGIS |
| Ö7 | Shards and replicas | A9 | "each index is divided into five primary shards and one replica"; "you can't easily change the number of primary shards"; 10–30 GiB / 30–50 GiB https://docs.aws.amazon.com/opensearch-service/latest/developerguide/bp-sharding.html | primary count fixed at creation |
| Ö8 | Near-real-time refresh and segments | A10 | "The default refresh interval is one second" https://docs.aws.amazon.com/opensearch-service/latest/developerguide/bp.html | no multi-document transaction; frequent updates are costly |
| Ö9 | Vector search and hybrid | A5 | k-NN / HNSW; pgvector comparison https://docs.aws.amazon.com/prescriptive-guidance/latest/retrieval-augmented-generation-options/rag-custom-retrievers.html | embeddings are separate work; exact codes need hybrid |

## All cases per concept

| Section | Concept | Cases (including the impossible one) |
|---|---|---|
| A2 | field types | text, keyword, number/date, boolean, geo, nested, knn_vector, new field (dynamic mapping), change type: **cannot** |
| A3 | analyzer | case, Turkish letters, stems, stop words, synonyms, keyword field, different analyzer at write and search (0 hits, live), change analyzer later: **cannot** |
| A4 | query paths | word, words, phrase, prefix, exact keyword, number range, infix: **cannot cheaply**, id read |
| A5 | score | rare token, common token, short field, boost, filter (no change), sort by field, numeric signal, non-matching document (**not scored**) |
| A5 | keyword vs vector vs hybrid | no shared word, exact code (vector **unreliable**), typo, filter, merging scores |
| A6 | fuzziness AUTO | 2 chars (exact; "tb" **cannot**), 4 chars, 7 chars, 3 edits (**cannot**), Turkish letters (analyzer) |
| A6 | prefix ways | prefix query, edge n-gram / search_as_you_type, completion, infix n-gram, prefix + typo |
| A7 | aggregation types | terms, range, date_histogram, metrics, cardinality (approximate), nested, text field (**cannot by default**), JOIN (**cannot**) |
| A8 | geo questions | distance, sort, bounding box, polygon, geo + text, road route (**cannot**), coordinate systems (limited) |
| A9 | shards and requests | id read, search, more replicas, change primary count (**cannot easily**), node failure, too many small shards, too large shard |
| A10 | life of a write | search before refresh, GET by id, update, delete, many updates, append-only, version condition, multi-document all-or-nothing (**cannot**) |

## Anatomy list and colors

- Core data structures: index, document (`_id`, `_source`), field and mapping, token, posting list, shard, segment.
- Colors: `_id` yellow (the identity), the searched text field blue, other fields grey (written in the A2 anatomy caption).

## Matrix products (A11)

PostgreSQL full text search (tsvector, GIN, pg_trgm, PostGIS, pgvector), Elasticsearch, Amazon OpenSearch Service.

## R1 catalog of the domain

Domain: database. Catalog: VM, ŞE, EY, OY, TA, DA, YD, AO (`R1_CATALOG`), unchanged.

## Use cases (M2): candidates, weights, results (model 2)

| No | Use case | Candidates (best fit first) | R1 sub-items | R1 weight | Totals /100 | sim |
|---|---|---|---|---|---|---|
| 1 | Product search with typos | os, aur, doc | EY, DA, AO | 46 | 84,4 / 68,4 / 64,7 | w_search |
| 2 | Faceted navigation (= DocumentDB card 8) | doc, os, aur | EY, AO, DA, ŞE | 42 | 77,6 / 76,8 / 68 | w_facets |
| 3 | Autocomplete | os, ec, aur | EY, DA, AO | 44 | 89 / 82,8 / 69,7 | none |
| 4 | Store and pickup-point finder (geo + text) | os, aur, ec | EY, VM, DA | 40 | 85,7 / 84,9 / 76,1 | none |
| 5 | Application log analytics | oss, os, cw | EY, OY, YD, DA | 44 | 85,6 / 81 / 75,6 | w_logs |
| 6 | Security analytics | os, oss, rs | EY, AO, DA, YD | 44 | 80,4 / 76,4 / 67,4 | none |
| 7 | Metrics dashboards (observability) | ix, cw, os | VM, EY, YD | 42 | 84,8 / 76,6 / 66,4 | w_metrics |
| 8 | Knowledge base search (keyword + vector) | aur, oss, os | EY, DA, AO | 38 | 90,2 / 82 / 70,6 | w_kb |
| 9 | E-commerce relevance tuning | os, aur, doc | AO, EY, OY, DA | 46 | 91,4 / 70 / 69,6 | none |
| 10 | Anomaly detection per category and city | os, ix, cw | AO, EY, VM | 42 | 88 / 70 / 69,6 | none |

- Clear losses of OpenSearch: card 7 (third, R1 loss: a time series engine fits), card 8 (third behind Aurora and its own Serverless twin).
- Another engine wins R1 but loses the total: card 2 (OpenSearch wins R1 40,8 to 30,4, DocumentDB wins the total), card 8 (OpenSearch wins R1, Aurora the total).
- Twin (Serverless) as candidate: cards 5 (Serverless wins: no node work, data in S3), 6 (domain wins: Security Analytics, Alerting, ISM are not in Serverless), 8.
- "Both together": cards 1, 2, 9 (catalog in DocumentDB, search copy in OpenSearch), 4 (record and delivery rule in Aurora/PostGIS, "near me" search in OpenSearch), 5 (CloudWatch subscription into OpenSearch).
- Services checked and left out: DynamoDB (no text search; its zero-ETL copy to OpenSearch is the DynamoDB answer), Neptune (no graph question), Amazon Location Service
  (not a database; routes), Kendra / Bedrock Knowledge Bases (managed retrieval; named in the head-to-head of card 8), Athena / Security Lake (not in the workshop;
  Redshift represents the SQL warehouse side in card 6), DocumentDB elastic cluster (same engine as DocumentDB; no write scale question).
- New entries (added only): `SVC["oss"] = "OpenSearch Serverless"`, `SVC["cw"] = "CloudWatch"`, `CATEGORY` and `LINK` for both (LINK points to this page).
- The ten titles follow the domain-map list (product search with typos, log analytics, faceted navigation, autocomplete, geo search for stores, security analytics,
  observability dashboards, document search in a knowledge base, e-commerce relevance tuning, anomaly detection on metrics).

## Consistency (decisions.md rule 10, printed with /tmp/os_mech.py before the reader)

- Twin rule: os and oss have the same R1 points on cards 5, 6, 8 (and the same reason text in R1).
- Copy durability (R3): os 8 when the rebuild takes an hour or more, 9 when minutes; oss 10 (managed storage); records (Aurora, DocumentDB) 10.
- Peak of a managed domain (R2): 9 with "node'lar önceden eklenir"; 8 on card 5 where incident searches compete with ingest.
- Update = reindex (OY): os 9 at about one update per second (card 9); 4 at hundreds per second on other pages.
- Code already counted in R1 (AO, EY) is not counted again in R4 (cards 9, 10 fixed before the reader).
- Aurora as a second copy of a DocumentDB catalog: R4 4 (cards 1, 2, 9), the same as DocumentDB card 8.
- Same workload on two pages: card 2 copies DocumentDB card 8 programmatically (rows, weights, points; asserted in code).

- Starting state (reader finding R1): cards 1, 3, 4, 9, 10 grow one Lale Market system (card 1 builds the domain); card 2 is the DocumentDB story before card 1; cards 5-8 start from zero with their own team.
- Reader report 2026-10-31: 20 findings, all closed (docs/opensearch.reader-report.md). Cross-page notes for the owner: Aurora uc-catalog OpenSearch ŞE 5 vs 2 here, ElastiCache uc-geo counts refresh in EY and YD, Aurora uc-geo/uc-catalog OpenSearch R3 3 and 4.

## Known traps (handled explicitly in Part A)

1. "Index" means a different thing than in a database → A2 note and concept card.
2. A term query on a text field returns 0 → A3 all-cases row and live O2 (B2).
3. Field type and analyzer cannot change → A2 and A3 "cannot" rows, reindex.
4. Primary shard count is fixed → A9 "cannot easily" row, quiz os-q4.
5. A write is searchable after a refresh; no multi-document transaction → A10, B7, M3 first row.
6. Vector search alone misses exact codes → A5 table.

## Live artifacts (from the live system, 2026-10-31)

| Structure | Artifact | How to take it |
|---|---|---|
| document | P0001 `_source`, S001 `_source` | `GET /opensearch/api/learn/item?lesson=search&id=P0001` |
| mapping and settings | 6 fields, tr_folded, 5 primaries, 1 replica, 200 documents, 71.807 bytes | `/opensearch/api/e2e/O8`, `/api/learn/index` |
| token | tr_folded vs standard | `/opensearch/api/e2e/O1` |
| posting list | term counts and first ids | `/opensearch/api/e2e/O2` |
| match and fuzziness | 5 hits with AUTO, 0 without | `/opensearch/api/e2e/O3`, `O4` |
| score | explain of P0136 (idf 3.3787, tf 0.4588) | `/opensearch/api/e2e/O6` |
| aggregation | 20 hits, 8 buckets | `/opensearch/api/e2e/O5` |
| geo | S010 10.04 km, S001 10.76 km, S019 12.55 km | `/opensearch/api/e2e/O7` |
| domain | `dbws-search` definition | `cloudformation/workshop.yaml` |

## Teaching data

`OS_PRODUCTS` (six real documents: P0001, P0031, P0081, P0016, P0044, P0175) and `OS_STORES` (six real stores). The inverted index of A4, the BM25 sim,
the shard sim and the fuzzy sim are computed from them; the geo sim returns the same three stores in the same order as the live index.

## Images

`opensearch-uses.png` (AWS docs), `opensearch-token-offsets.png`, `opensearch-index-shards.png`, `opensearch-cluster.png`, `opensearch-replicas.png`
(OpenSearch Project docs, Apache 2.0), `opensearch-great-circle.png` (Wikimedia Commons, CC BY-SA 4.0). Records in `app/engine_app/e2e/images.yaml`;
the three not on main came from the earlier attempt with their licence records. Own drawings: the A3 analyzer flow, the A4 posting lists, the A5 hybrid flow,
the A7 aggregation flow, the A10 refresh flow, the B7 copy flow.

## Prices (AWS Price List API, eu-central-1, 2026-10-26)

r6g.large.search $0.202/h, m6g.large.search $0.153/h, gp3 $0.1452/GB-month; Serverless OCU $0.339/h, hot $0.36/GB-month, warm $0.026/GB-month;
OpenSearch Ingestion OCU $0.310/h; CloudWatch Logs $0.63/GB ingested, $0.0324/GB-month stored, Logs Insights $0.0063/GB scanned, custom metric $0.30/month
(first 10,000), alarm $0.10/month; Timestream for InfluxDB db.influx.medium Multi-AZ $0.289/h. Serverless NextGen scale to zero and AWS pricing example 10
(about $250/month): https://aws.amazon.com/opensearch-service/pricing/
