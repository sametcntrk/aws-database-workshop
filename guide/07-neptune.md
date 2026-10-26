# Modül 7 - Neptune Serverless (Semi-structured · Graph)

**Domain dilimi:** birlikte satın alınanlar grafı. **Read:** openCypher, "C00001'in aldıklarını alan müşteriler başka ne aldı?"
**Bağlantı:** HTTPS 8182, openCypher HTTP endpoint'i, **IAM SigV4** (IAM DB authentication açık, şifre yok).

## 7.1 DB security group

Name `dbws-sg-db-neptune`, Inbound: **TCP 8182**, Source `dbws-sg-app-neptune`.

## 7.2 Subnet group

**Neptune → Subnet groups → Create DB subnet group**: Name `dbws-neptune`, VPC `dbws-vpc`, subnet'ler `dbws-data-a/b/c`.

## 7.3 Neptune cluster

**Neptune → Databases → Create database**

| Alan | Değer |
|---|---|
| Engine type | Provisioned (Serverless instance class ile) |
| Version | en güncel 1.4.x / 1.5.x |
| DB cluster identifier | `dbws-neptune` |
| Templates | Development and Testing |
| Instance class | **Serverless**, Min **1** NCU, Max **8** NCU |
| Multi-AZ deployment | **Create read replica in different zone** |
| VPC / Subnet group | `dbws-vpc` / `dbws-neptune` |
| Security group | sadece `dbws-sg-db-neptune` |
| Availability Zone | eu-central-1b (writer) |
| Additional → IAM DB authentication | **açık** |
| Encryption | açık |
| Backup retention | 1 day; Deletion protection kapalı |

Oluşturma 15-20 dk. Not alın:
- **Cluster endpoint:** `dbws-neptune.cluster-xxxx.eu-central-1.neptune.amazonaws.com`, port 8182
- **Cluster resource ID:** Configuration sekmesi, `cluster-XXXXXXXXXXXX`

## 7.4 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-neptune` |
| E2 role | `dbws-app-neptune-eu-central-1` |
| E3 | Subnet `dbws-app-b`, IP `10.20.11.11` |
| E4 | `dbws-tg-neptune`, health check `/neptune/health` |
| E5 | Path `/neptune`, `/neptune/*`, öncelik **70** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["neptune-db:connect", "neptune-db:ReadDataViaQuery", "neptune-db:WriteDataViaQuery", "neptune-db:DeleteDataViaQuery"],
      "Resource": "arn:aws:neptune-db:eu-central-1:<ACCOUNT_ID>:<cluster resource ID>/*" }
  ]
}
```

```bash
ENGINE=neptune
URL_PREFIX=/neptune
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
NEPTUNE_HOST=<cluster endpoint>
NEPTUNE_PORT=8182
```

## 7.5 Doğrulama

`/neptune/` → **Seed** (Customer ve Product düğümleri, BOUGHT kenarları) → **Read** (3 adımlık gezinme).
İlişkisel modelde aynı soru üç JOIN gerektirirdi; grafta kenarlar indeksli olduğu için gezinme maliyeti ilişki sayısıyla büyür, tablo boyutuyla değil.
