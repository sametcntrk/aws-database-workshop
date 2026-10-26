# Modül 3 - DynamoDB (Semi-structured, Key-value)

- **Sitedeki bölüm:** sepet (`/cart`) ve ürün sayfasındaki "Add to cart" düğmesi
- **Bağlantı:** HTTPS 443, DynamoDB API, IAM SigV4 (şifre yok). Trafik S3/DynamoDB gateway endpoint'inden geçer, NAT kullanmaz.
- **Neden DynamoDB?** Sepet her zaman aynı anahtarla okunur: "bu ziyaretçinin sepeti". DynamoDB bu erişimi her ölçekte birkaç milisaniyede yapar.

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

Tablo oluştuktan sonra iki ayar yapın:
- **Backups → Point-in-time recovery → Edit → Turn on**
- **Additional settings → Time to Live (TTL) → Turn on**: TTL attribute name `expires_at`.
  Sepet kalemleri 24 saat sonra kendiliğinden silinir. TTL silmeleri ücretsizdir.

Table ARN'ini not alın.

## 3.2 Engine App

DynamoDB bölgesel bir servistir. VPC içinde DB security group yoktur. Erişimi IAM kontrol eder.

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-dynamodb` |
| E2 role | `dbws-app-dynamodb-eu-central-1` |
| E3 | Subnet `dbws-app-a`, IP `10.20.10.11` |
| E4 | `dbws-tg-dynamodb`, health check `/dynamodb/health` |
| E5 | Path `/cart`, `/dynamodb/*`, öncelik **30** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["dynamodb:DescribeTable", "dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem",
                 "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem"],
      "Resource": "arn:aws:dynamodb:eu-central-1:<ACCOUNT_ID>:table/dbws-cart" },
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
  ]
}
```

```bash
ENGINE=dynamodb
URL_PREFIX=/dynamodb
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
TABLE_NAME=dbws-cart
```

## 3.3 Doğrulama

1. Bir ürün sayfasında **Add to cart** düğmesine basın. Panelde `UpdateItem` ve harcanan yazma birimini (WRU) görün.
2. Aynı ürünü 5 adet olarak iki kez ekleyin. İkinci seferde koşullu yazma reddedilir: bir üründen en fazla 5 adet alınabilir.
3. `/cart` sayfasında **Eventually consistent** seçin. Paneldeki okuma biriminin (RRU) yarıya indiğini görün.
4. **Start the simulation** düğmesine basın. Saniyedeki yazma sayısını ve gecikmeyi görün. Bir çalıştırma en fazla 2.000 istek gönderir.
