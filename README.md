# AWS Database Workshop

"How to Choose Database" infografiğinin AWS sütunundaki her veri tipi için bir **Engine** ve ona bağlı bir **Engine App** (EC2).
Her Engine App kendi e-ticaret verisini üretir (**Seed**), kendi Engine'ine yazar, geri okur (**Read**) ve web sayfasında gösterir.

| Veri tipi | Kategori | Engine | Domain dilimi |
|---|---|---|---|
| Structured | Relational | Aurora PostgreSQL Serverless v2 | müşteriler ve siparişler |
| Structured | Columnar | Redshift Serverless | satış analitiği |
| Semi-structured | Key-value | DynamoDB | alışveriş sepeti |
| Semi-structured | In-memory | ElastiCache Serverless (Valkey) | oturumlar, liderlik tablosu |
| Semi-structured | Wide column | Keyspaces | kullanıcı aktivite akışı |
| Semi-structured | Time-series | Timestream for InfluxDB | depo sensör verisi |
| Semi-structured | Graph | Neptune Serverless | birlikte satın alınanlar |
| Semi-structured | Document | DocumentDB | ürün kataloğu |
| Unstructured | Blob | S3 | ürün görselleri |
| Unstructured | Text search + Geospatial | OpenSearch Service | ürün arama, mağaza konumu |

QLDB (destek sonu 31.07.2025), CloudSearch ve Timestream for LiveAnalytics (yeni müşterilere kapalı) workshop'ta yok.

## İçerik

| Yol | Ne |
|---|---|
| `docs/aws-database-workshop-architecture.drawio.png` | Mimari diyagram (draw.io, düzenlenebilir PNG) |
| `docs/aws-database-workshop-data-type-mapping.drawio.png` | Veri tipi → Engine eşleştirmesi |
| `cloudformation/workshop.yaml` | Eğitmen için tek parça CloudFormation template |
| `guide/` | Katılımcılar için adım adım Console rehberi (aynı yapı, aynı değerler) |
| `app/` | Engine App kodu (Flask, engine başına adapter) |
| `GLOSSARY.md` | Workshop terimleri |

## Eğitmen: tek adımda kurulum

```bash
aws cloudformation deploy --region eu-central-1 \
  --stack-name dbws-workshop \
  --template-file cloudformation/workshop.yaml \
  --s3-bucket <template-yukleme-bucketi> \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides HostedZoneId=<Z...> DomainName=dbworkshop.tdsynnexlab.link
```

Kurulum yaklaşık 30-40 dakika sürer (OpenSearch, DocumentDB, Neptune ve Aurora en uzun bekleyenlerdir).
Sonra `https://dbworkshop.tdsynnexlab.link/` adresini açın. Silmek için: `aws cloudformation delete-stack --stack-name dbws-workshop`.

Template 51.200 baytı geçtiği için CLI ile `--s3-bucket` gerekir; Console'dan yüklerken CloudFormation bunu kendisi yapar.
Hesapta `AWSServiceRoleForAmazonOpenSearchService` zaten varsa `CreateOpenSearchServiceLinkedRole=false` verin.

## Geliştirme

`cloudformation/workshop.yaml` dosyasını elle değil `cloudformation/src/gen_template.py` ile üretin.
Diyagram `docs/diagram-src/gen_workshop_diagram.py` ile üretilir.
