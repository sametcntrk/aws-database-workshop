# Modül 1 - Aurora PostgreSQL Serverless v2 (Structured, Relational)

- **Sitedeki bölüm:** ödeme (`/checkout`), siparişlerim (`/orders`), sipariş raporu (`/admin/orders`)
- **Bağlantı:** PostgreSQL wire protokolü, TCP 5432, TLS. Kullanıcı adı ve şifre, RDS'in yönettiği secret'tadır.
- **Neden Aurora?** Bir sipariş birden fazla tabloyu aynı anda değiştirir: stok düşer, sipariş ve kalemleri yazılır.
  Bunların hepsi ya birlikte olmalı ya da hiç olmamalı. Bunu ACID transaction sağlar.

## 1.1 Zero-ETL için parametre grubu

Aurora, siparişleri Redshift'e **zero-ETL integration** ile kendiliğinden kopyalar (Modül 2).
Bunun için Aurora'nın özel bir cluster parametre grubuna ihtiyacı vardır.

**RDS → Parameter groups → Create parameter group**

| Alan | Değer |
|---|---|
| Parameter group family | `aurora-postgresql17` |
| Type | DB Cluster Parameter Group |
| Group name | `dbws-aurora-zeroetl` |

Grubu açın, **Edit** seçin ve dört parametreyi ayarlayın:

| Parametre | Değer |
|---|---|
| `rds.logical_replication` | `1` |
| `aurora.enhanced_logical_replication` | `1` |
| `aurora.logical_replication_backup` | `0` |
| `aurora.logical_replication_globaldb` | `0` |

> Bu parametreler statiktir. Çalışan bir cluster'da değiştirirseniz, writer instance'ı yeniden başlatmanız gerekir.
> Cluster'ı bu grupla oluşturursanız yeniden başlatma gerekmez.

## 1.2 DB security group ve subnet group

- Security group: Name `dbws-sg-db-aurora`, VPC `dbws-vpc`. Inbound: **PostgreSQL TCP 5432**, kaynak `dbws-sg-app-aurora`.
- **RDS → Subnet groups → Create DB subnet group**: Name `dbws-aurora`, VPC `dbws-vpc`, subnet'ler `dbws-data-a/b/c`.

## 1.3 Aurora cluster

**RDS → Databases → Create database → Full configuration**

| Alan | Değer |
|---|---|
| Engine | Aurora (PostgreSQL Compatible), version **17.9** |
| Templates | Dev/Test |
| DB cluster identifier | `dbws-aurora` |
| Master username | `dbwsadmin` |
| Credentials management | **Managed in AWS Secrets Manager** (KMS key: aws/secretsmanager) |
| Cluster storage configuration | Aurora Standard |
| Instance configuration | **Serverless v2**, en az **0.5 ACU**, en çok **4 ACU** |
| Availability & durability | **Create an Aurora Replica in a different AZ** |
| VPC ve DB subnet group | `dbws-vpc` ve `dbws-aurora` |
| Public access | No |
| VPC security group | Choose existing: yalnızca `dbws-sg-db-aurora` (default'u kaldırın) |
| Availability Zone | eu-central-1a (writer) |
| Additional configuration → Initial database name | `shop` |
| Additional configuration → DB cluster parameter group | `dbws-aurora-zeroetl` |
| Backup retention | 1 day |
| Encryption | açık (aws/rds) |
| Deletion protection | kapalı |

İsterseniz instance'ları `dbws-aurora-writer` (AZ a) ve `dbws-aurora-reader` (AZ b) olarak adlandırın.
Oluşturma 10-15 dakika sürer. Beklerken 1.4'e geçin.

Şu iki değeri not alın:
- **Writer endpoint:** Connectivity & security sekmesinde, `dbws-aurora.cluster-xxxx.eu-central-1.rds.amazonaws.com`
- **Secret ARN:** Configuration sekmesinde, Master credentials ARN (`arn:aws:secretsmanager:...:secret:rds!cluster-...`)

## 1.4 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-aurora` |
| E2 role | `dbws-app-aurora-eu-central-1` |
| E3 | Subnet `dbws-app-a`, IP `10.20.10.14` |
| E4 | `dbws-tg-aurora`, health check `/aurora/health` |
| E5 | Path `/checkout`, `/orders`, `/admin/orders`, `/aurora/*`, öncelik **10** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<Aurora master credentials secret ARN>" },
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
  ]
}
```

```bash
ENGINE=aurora
URL_PREFIX=/aurora
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
DB_HOST=<writer endpoint>
DB_PORT=5432
DB_NAME=shop
DB_SECRET_ARN=<Aurora master credentials secret ARN>
```

## 1.5 Doğrulama

1. Admin Console'da Aurora satırındaki **Seed** düğmesine basın.
2. Bir ürünü sepete ekleyin (DynamoDB gerekir) ve `/checkout` sayfasını açın. **Place the order** düğmesine basın.
3. Panelde `BEGIN`, stok `UPDATE`, iki `INSERT` ve `COMMIT` satırlarını görün.
4. Sepete yine bir ürün ekleyin. **Make the payment fail after the stock update** kutusunu işaretleyip siparişi verin.
   Bu kez panelde `ROLLBACK` görünür: stok geri gelir ve sipariş oluşmaz.
5. `/orders` sayfasında siparişinizi görün. `/admin/orders` sayfasında **EXPLAIN ANALYZE** deneyini açın.
