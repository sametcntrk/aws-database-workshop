# Modül 8 - Amazon DocumentDB (Semi-structured · Document)

**Domain dilimi:** ürün kataloğu. **Read:** iç içe alanla filtre (`attributes.renk`) ve kategoriye göre aggregation.
**Bağlantı:** MongoDB wire protokolü, TCP 27017, TLS (RDS CA bundle), kullanıcı adı/şifre (`dbws/docdb` secret'ı).

## 8.1 Secret

```bash
PW=$(aws secretsmanager get-random-password --password-length 32 --exclude-punctuation \
     --require-each-included-type --query RandomPassword --output text)
aws secretsmanager create-secret --region eu-central-1 --name dbws/docdb \
  --description "DocumentDB admin user for the DocumentDB Engine App" \
  --secret-string "{\"username\":\"dbwsadmin\",\"password\":\"$PW\"}"
echo "$PW"
```

## 8.2 DB security group ve subnet group

- Security group `dbws-sg-db-docdb`, Inbound: **TCP 27017**, Source `dbws-sg-app-docdb`.
- **DocumentDB → Subnet groups → Create**: Name `dbws-docdb`, VPC `dbws-vpc`, subnet'ler `dbws-data-a/b/c`.

## 8.3 Cluster

**Amazon DocumentDB → Clusters → Create → Instance-based cluster**

| Alan | Değer |
|---|---|
| Cluster identifier | `dbws-docdb` |
| Engine version | **8.0.0** |
| Instance class | `db.r6g.large` |
| Number of instances | **2** |
| Username / Password | `dbwsadmin` / 8.1'deki şifre (Self managed) |
| Show advanced settings → VPC / Subnet group | `dbws-vpc` / `dbws-docdb` |
| Security groups | sadece `dbws-sg-db-docdb` |
| Encryption | açık; Backup retention 1 day; Deletion protection kapalı |

İsteğe bağlı: instance'ları `dbws-docdb-1` (AZ b) ve `dbws-docdb-2` (AZ c) olarak adlandırın.
Oluşturma 10-15 dk. **Cluster endpoint**'i not alın: `dbws-docdb.cluster-xxxx.eu-central-1.docdb.amazonaws.com`.

## 8.4 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-docdb` |
| E2 role | `dbws-app-docdb-eu-central-1` |
| E3 | Subnet `dbws-app-b`, IP `10.20.11.12` |
| E4 | `dbws-tg-docdb`, health check `/docdb/health` |
| E5 | Path `/docdb`, `/docdb/*`, öncelik **80** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/docdb secret ARN>" }
  ]
}
```

```bash
ENGINE=docdb
URL_PREFIX=/docdb
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
DB_HOST=<cluster endpoint>
DB_PORT=27017
DB_SECRET_ARN=<dbws/docdb secret ARN>
```

## 8.5 Doğrulama

`/docdb/` → **Seed** (`products` koleksiyonu + bileşik indeks) → **Read** (filtre + aggregation).
Uygulama okumaları `secondaryPreferred` ile replica'ya gönderir; yazmalar primary'ye gider.
