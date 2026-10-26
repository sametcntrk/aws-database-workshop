# AWS Database Workshop - Katılımcı Rehberi

Bu rehberle eğitmenin CloudFormation ile tek adımda kurduğu yapının **aynısını** AWS Console'dan kendiniz kurarsınız.
Bütün isimler, CIDR blokları, portlar ve boyutlar `cloudformation/workshop.yaml` ile birebir aynıdır.

![Mimari](../docs/aws-database-workshop-architecture.drawio.png)

## Nasıl ilerlenir

1. **Modül 0'ı** baştan sona yapın (zorunlu): ağ, endpoint'ler, ALB, sertifika ve DNS.
2. Engine modüllerinden istediklerinizi, istediğiniz sırayla yapın. Her modül bağımsızdır.
3. Her modülün sonunda **Doğrulama** adımı vardır: Engine App sayfasında **Seed** ve **Read** çalışıyorsa modül tamamdır.
4. Workshop bitince **Temizlik** bölümünü uygulayın; aksi halde ücretlendirme sürer.

| Modül | Engine | Veri tipi · Kategori | Kurulum süresi (bekleme dahil) |
|---|---|---|---|
| [0](00-ortak-altyapi.md) | Ortak altyapı | - | 40 dk |
| [1](01-aurora.md) | Aurora PostgreSQL Serverless v2 | Structured · Relational | 20 dk |
| [2](02-redshift.md) | Redshift Serverless | Structured · Columnar | 15 dk |
| [3](03-dynamodb.md) | DynamoDB | Semi-structured · Key-value | 10 dk |
| [4](04-elasticache.md) | ElastiCache Serverless (Valkey) | Semi-structured · In-memory | 15 dk |
| [5](05-keyspaces.md) | Keyspaces | Semi-structured · Wide column | 10 dk |
| [6](06-influxdb.md) | Timestream for InfluxDB | Semi-structured · Time-series | 25 dk |
| [7](07-neptune.md) | Neptune Serverless | Semi-structured · Graph | 25 dk |
| [8](08-docdb.md) | DocumentDB | Semi-structured · Document | 20 dk |
| [9](09-s3.md) | S3 | Unstructured · Blob | 10 dk |
| [10](10-opensearch.md) | OpenSearch Service | Unstructured · Text search + Geo | 30 dk |
| [T](99-temizlik.md) | Temizlik | - | 20 dk |

Uzun bekleyen kaynaklarda (OpenSearch, Neptune, DocumentDB, InfluxDB, Aurora) oluşturma başlatıldıktan sonra
aynı modülün IAM role ve security group adımlarına geçebilirsiniz; her modül hangi adımların paralel yapılabileceğini söyler.

## Ön koşullar

- **Region:** Europe (Frankfurt) `eu-central-1`. Konsolun sağ üstünden seçin; bütün modüller bu region'dadır.
- Yönetici (AdministratorAccess) yetkisi olan bir IAM kullanıcısı veya rolü.
- Route 53'te public bir hosted zone. Workshop hesabında: `tdsynnexlab.link`. Kendi hesabınızda kendi alan adınızı kullanın ve aşağıdaki `dbworkshop.tdsynnexlab.link` değerini değiştirin.
- Hesapta en az 3 boş Elastic IP kotası ve 1 boş VPC kotası.

## Ortak değerler

| Ad | Değer |
|---|---|
| İsim öneki | `dbws` |
| VPC CIDR | `10.20.0.0/16` |
| Public subnet'ler | `10.20.0.0/24` (a), `10.20.1.0/24` (b), `10.20.2.0/24` (c) |
| App subnet'leri | `10.20.10.0/24` (a), `10.20.11.0/24` (b), `10.20.12.0/24` (c) |
| Data subnet'leri | `10.20.20.0/24` (a), `10.20.21.0/24` (b), `10.20.22.0/24` (c) |
| Alan adı | `dbworkshop.tdsynnexlab.link` |
| Engine App kod deposu | `https://github.com/sametcntrk/aws-database-workshop.git` (dal `main`) |
| Engine App AMI | Amazon Linux 2023 (arm64) |
| Engine App instance tipi | `t4g.medium` |

| Engine App | AZ / subnet | Sabit private IP | ALB path | Öncelik |
|---|---|---|---|---|
| Aurora | a / `dbws-app-a` | `10.20.10.14` | `/aurora/*` | 10 |
| Redshift | c / `dbws-app-c` | `10.20.12.12` | `/redshift/*` | 20 |
| DynamoDB | a / `dbws-app-a` | `10.20.10.11` | `/dynamodb/*` | 30 |
| ElastiCache | b / `dbws-app-b` | `10.20.11.13` | `/elasticache/*` | 40 |
| Keyspaces | a / `dbws-app-a` | `10.20.10.13` | `/keyspaces/*` | 50 |
| InfluxDB | c / `dbws-app-c` | `10.20.12.13` | `/influxdb/*` | 60 |
| Neptune | b / `dbws-app-b` | `10.20.11.11` | `/neptune/*` | 70 |
| DocumentDB | b / `dbws-app-b` | `10.20.11.12` | `/docdb/*` | 80 |
| S3 | a / `dbws-app-a` | `10.20.10.12` | `/s3/*` | 90 |
| OpenSearch | c / `dbws-app-c` | `10.20.12.11` | `/opensearch/*` | 100 |

Terimler için [GLOSSARY.md](../GLOSSARY.md) dosyasına bakın.
