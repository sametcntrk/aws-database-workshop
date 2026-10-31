# Scope: 00 Veri nedir? (E2E, TR)

Owner request (2026-10-31): "E2E'ye 00 ekle: data nedir, data types, data saklama formatları ve sorgulamaları, JDBC connection, OLTP/OLAP, HDFS/NTFS vs." Grilling answers: own page `/e2etutorial/veri` first in the list; the author picks the order; add ACID/BASE, normalization/denormalization, row/column storage, schema-on-write/schema-on-read (no CAP); four simulations; e2e-tech-tutorial writing, check, reader and source rules, but no weighted use case cards (the page is not one service).

## Decisions
- Not an Engine: `e2e/index.yaml` `intro` block (num 00), route accepts it, `_base.html` shows "Tutorial 00", pager goes to Aurora. Aurora stays 01.
- Order: A (data itself) A1 veri/bilgi/kayıt/metadata, A2 tipler, A3 yapı ve şema, A4 modeller + normalizasyon, A5 ACID/BASE; B (saklama) B1 satır/sütun, B2 dosya biçimleri, B3 depolama türleri ve dosya sistemleri; C (kullanma) C1 sorgu dilleri, C2 sürücü/JDBC/connection string/havuz, C3 OLTP/OLAP/ETL/ELT/zero-ETL, C4 warehouse/lake/lakehouse, C5 harita.
- Simulations (`e2e_veri.py`, data from `e2e_sims`): rowcol, formats, connect, oltp_olap.
- Pictures: own flow and placement drawings; no external images.

## Facts and sources
- PostgreSQL types, ranges, sizes, 1 GB text: postgresql.org/docs/current/datatype*.html. 8 KB page.
- Redshift 1 MB blocks; DynamoDB Number 38 digits.
- NTFS 4 KB default cluster (≤16 TB): learn.microsoft.com default cluster size article. ext4 "genellikle 4 KB".
- HDFS 128 MB block, replication 3: HdfsDesign.
- S3: single PUT 5 GB; max object 50 TB since Dec 2025 (aws.amazon.com/about-aws/whats-new/2025/12/amazon-s3-maximum-object-size-50-tb/); 11 nines design.
- PostgreSQL protocol messages and SCRAM flow: protocol-flow.html. Ports and libraries: read from app/engine_app/engines/*.py.
- Zero-ETL lag ~30 s: measured 2026-10-31, two runs (poller started before the order).
- Live artifact: GET /docdb/api/product/P0001 (2026-10-31).

## Checks
- clarity TR: OK (28 definitions, longest plain run 3).
- Browser: 4 simulations to the last step, 14/14 checkpoints, no overflowing table, no console error.
- Reader report: docs/veri.reader-report.md, 17 findings, all closed (B16 partly: shared legend).
