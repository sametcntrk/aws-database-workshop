# Modül 3 - DynamoDB (Semi-structured · Key-value)

**Domain dilimi:** alışveriş sepeti. **Read:** `Query(pk = CART#C00001)`.
**Bağlantı:** HTTPS 443, DynamoDB API, IAM SigV4 (şifre yok), **S3/DynamoDB gateway endpoint** üzerinden (NAT yok).

## 3.1 Tablo

**DynamoDB → Tables → Create table**

| Alan | Değer |
|---|---|
| Table name | `dbws-cart` |
| Partition key | `pk` (String) |
| Sort key | `sk` (String) |
| Table settings | **Customize settings** |
| Capacity mode | **On-demand** |
| Encryption | Owned by Amazon DynamoDB |

Oluştuktan sonra **Backups → Point-in-time recovery → Edit → Turn on**. Table ARN'ini not alın.

## 3.2 Engine App

VPC içinde DB security group yok: DynamoDB bölgesel bir servistir, erişim IAM ile kontrol edilir.

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-dynamodb` |
| E2 role | `dbws-app-dynamodb-eu-central-1` |
| E3 | Subnet `dbws-app-a`, IP `10.20.10.11` |
| E4 | `dbws-tg-dynamodb`, health check `/dynamodb/health` |
| E5 | Path `/dynamodb`, `/dynamodb/*`, öncelik **30** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["dynamodb:DescribeTable", "dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem",
                 "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem"],
      "Resource": "arn:aws:dynamodb:eu-central-1:<ACCOUNT_ID>:table/dbws-cart" }
  ]
}
```

```bash
ENGINE=dynamodb
URL_PREFIX=/dynamodb
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
TABLE_NAME=dbws-cart
```

## 3.3 Doğrulama

`/dynamodb/` → **Seed** → **Read**. Sonra DynamoDB konsolunda **Explore items → Query**: `pk = CART#C00001`.
Sonucu bir **Scan** ile karşılaştırın: Query tek partition okur, Scan bütün tabloyu.
