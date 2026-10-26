# AWS Database Workshop - Lale Market

"How to Choose Database" infografiğinin AWS sütunundaki her veri tipi için bir **Engine** ve ona bağlı bir **Engine App** (EC2) vardır.
On Engine App birlikte **Lale Market** adlı bir e-ticaret sitesini oluşturur. Sitenin her bölümü farklı bir veritabanını kullanır.
Sağdaki **Behind the scenes** paneli her tıklamada hangi veritabanına hangi sorgunun gittiğini, süresini, ağ yolunu ve maliyetini gösterir.
Her bölümde adım adım bir **Tutorial**, karşılaştırma yapılabilen **Experiment**'lar ve uçtan uca bir **Guided journey** vardır.

| Veri tipi | Kategori | Engine | Sitedeki bölüm | Yollar |
|---|---|---|---|---|
| Semi-structured | Document | DocumentDB | Ana sayfa, kategori, ürün, Admin Console | `/`, `/c/*`, `/p/*`, `/admin` |
| Unstructured | Text search + Geo | OpenSearch Service | Arama, mağaza bulucu | `/search`, `/stores` |
| Semi-structured | Graph | Neptune Serverless | Öneriler, müşteri grafı | `/admin/graph` |
| Semi-structured | Key-value | DynamoDB | Sepet | `/cart` |
| Structured | Relational | Aurora PostgreSQL Serverless v2 | Ödeme, siparişlerim, sipariş raporu | `/checkout`, `/orders`, `/admin/orders` |
| Semi-structured | In-memory | ElastiCache Serverless (Valkey) | Flaş indirim, canlı liderlik tablosu | `/deals`, `/admin/live` |
| Semi-structured | Wide column | Keyspaces | Aktivite geçmişi | `/account/activity` |
| Unstructured | Blob | S3 | Ürün görselleri, satıcı paneli | `/seller` |
| Structured | Columnar | Redshift Serverless | Satış raporları (Aurora'dan zero-ETL ile canlı) | `/admin/reports` |
| Semi-structured | Time-series | Timestream for InfluxDB | Operasyon ekranı | `/admin/ops` |

QLDB (destek sonu 31.07.2025), CloudSearch ve Timestream for LiveAnalytics (yeni müşterilere kapalı) workshop'ta yoktur.

## İçerik

| Yol | Ne |
|---|---|
| `docs/aws-database-workshop.drawio` | Mimari ve veri tipi eşleştirmesi (2 sayfa, düzenlenebilir) |
| `docs/*.drawio.png` | Aynı diyagramların PNG hali |
| `docs/storefront-spec.md` | Mağazanın tasarım özeti |
| `docs/adr/` | Mimari kararlar (zero-ETL, sayfaların tarayıcıda birleşmesi) |
| `cloudformation/workshop.yaml` | Eğitmen için tek parça CloudFormation template |
| `guide/` | Katılımcılar için adım adım Console rehberi (aynı yapı, aynı değerler) |
| `app/` | Engine App kodu: Flask, engine başına bir modül, Tutorial metinleri (`app/engine_app/tutorials/`) |
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

Kurulum yaklaşık 40-50 dakika sürer. OpenSearch, DocumentDB, Neptune, Aurora ve zero-ETL integration en uzun bekleyenlerdir.

Kurulumdan sonra:

1. Yönetici anahtarını okuyun:
   `aws secretsmanager get-secret-value --secret-id dbws/admin --query SecretString --output text`
2. `https://dbworkshop.tdsynnexlab.link/admin` adresini açın, anahtarı girin ve **Seed all Engines** düğmesine basın.
3. Aynı sayfada **Connect zero-ETL** düğmesine basın.
4. `https://dbworkshop.tdsynnexlab.link/` adresini açın ve **Start the guided journey** düğmesine basın.

Silmek için: `aws cloudformation delete-stack --region eu-central-1 --stack-name dbws-workshop`.

Notlar:
- Template 51.200 baytı geçtiği için CLI ile `--s3-bucket` gerekir. Console'dan yüklerken CloudFormation bunu kendisi yapar.
- Hesapta `AWSServiceRoleForAmazonOpenSearchService` zaten varsa `CreateOpenSearchServiceLinkedRole=false` verin.
- Var olan bir stack'e zero-ETL eklerken önce `EnableZeroEtl=false` ile deploy edin. Aurora üyelerinin parametre durumu
  `in-sync` olunca (gerekirse writer'ı yeniden başlatın) `EnableZeroEtl=true` ile tekrar deploy edin.
- Load Simulation maliyeti sınırlıdır: bir çalıştırma en fazla 2.000 istek, ziyaretçi başına saatte 3 çalıştırma. Admin Console'dan kapatılabilir.

## Geliştirme

- `cloudformation/workshop.yaml` dosyasını elle değil `cloudformation/src/gen_template.py` ile üretin, sonra `cfn-lint` çalıştırın.
- Diyagram `docs/diagram-src/gen_workshop_diagram.py` ile üretilir.
- Bir Engine App'i yerelde denemek için: `ENGINE=dynamodb TABLE_NAME=... flask --app engine_app.web run` (`app/` klasöründe).
