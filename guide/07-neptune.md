# Modül 7 - Neptune Serverless (Semi-structured, Graph)

- **Sitedeki bölüm:** ürün sayfasındaki öneriler ve müşteri grafı (`/admin/graph`)
- **Bağlantı:** HTTPS 8182, openCypher HTTP endpoint'i, **IAM SigV4**. IAM DB authentication açıktır, şifre yoktur.
- **Neden Neptune?** "Bu ürünü alanlar başka ne aldı?" sorusu, ilişkiler üzerinde gezinmektir.
  İlişkisel modelde her adım yeni bir JOIN olur. Grafta kenarlar hazırdır ve gezinme hızlıdır.

## 7.1 DB security group ve subnet group

- Security group `dbws-sg-db-neptune`. Inbound: **TCP 8182**, kaynak `dbws-sg-app-neptune`.
- **Neptune → Subnet groups → Create DB subnet group**: Name `dbws-neptune`, VPC `dbws-vpc`, subnet'ler `dbws-data-a/b/c`.

## 7.2 Neptune cluster

**Neptune → Databases → Create database**

| Alan | Değer |
|---|---|
| Engine type | Provisioned (Serverless instance class ile) |
| Version | en güncel 1.4.x veya 1.5.x |
| DB cluster identifier | `dbws-neptune` |
| Templates | Development and Testing |
| Instance class | **Serverless**, en az **1** NCU, en çok **8** NCU |
| Multi-AZ deployment | **Create read replica in different zone** |
| VPC ve subnet group | `dbws-vpc` ve `dbws-neptune` |
| Security group | yalnızca `dbws-sg-db-neptune` |
| Availability Zone | eu-central-1b (writer) |
| Additional → IAM DB authentication | **açık** |
| Encryption | açık |
| Backup retention | 1 day. Deletion protection kapalı. |

Oluşturma 15-20 dakika sürer. Şu iki değeri not alın:
- **Cluster endpoint:** `dbws-neptune.cluster-xxxx.eu-central-1.neptune.amazonaws.com`, port 8182
- **Cluster resource ID:** Configuration sekmesinde, `cluster-XXXXXXXXXXXX`

## 7.3 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-neptune` |
| E2 role | `dbws-app-neptune-eu-central-1` |
| E3 | Subnet `dbws-app-b`, IP `10.20.11.11` |
| E4 | `dbws-tg-neptune`, health check `/neptune/health` |
| E5 | Path `/admin/graph`, `/neptune/*`, öncelik **70** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["neptune-db:connect", "neptune-db:ReadDataViaQuery", "neptune-db:WriteDataViaQuery", "neptune-db:DeleteDataViaQuery"],
      "Resource": "arn:aws:neptune-db:eu-central-1:<ACCOUNT_ID>:<cluster resource ID>/*" },
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
  ]
}
```

```bash
ENGINE=neptune
URL_PREFIX=/neptune
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
NEPTUNE_HOST=<cluster endpoint>
NEPTUNE_PORT=8182
```

## 7.4 Doğrulama

1. Admin Console'da Neptune satırındaki **Seed** düğmesine basın. Müşteri ve ürün düğümleri ile BOUGHT kenarları yazılır.
2. Bir ürün sayfası açın. "Customers who bought this also bought" bölümünü ve paneldeki openCypher sorgusunu görün.
3. **For my persona** seçin. Öneri artık sizin satın aldıklarınızdan yola çıkar (3 adım).
4. `/admin/graph` sayfasında önce **Lukas Weber**, sonra **Ayşe Yılmaz** seçin. Lukas yalnızca kitap aldığı için grafı dardır.
   **Elif Kaya** seçin: hiç siparişi yoktur, bu yüzden grafı boştur. Buna soğuk başlangıç sorunu denir.
