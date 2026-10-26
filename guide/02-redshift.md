# Modül 2 - Redshift Serverless (Structured, Columnar)

- **Sitedeki bölüm:** satış raporları (`/admin/reports`)
- **Bağlantı:** PostgreSQL wire protokolü, TCP 5439, TLS. Kullanıcı adı ve şifre `dbws/redshift` secret'ındadır.
- **Neden Redshift?** Rapor sorguları milyonlarca satırı tarar ama yalnızca birkaç sütun okur. Redshift her sütunu ayrı saklar,
  bu yüzden yalnızca gereken sütunları diskten okur.
- **Zero-ETL:** Aurora'daki siparişler, kod yazmadan, saniyeler içinde Redshift'e kopyalanır. Bu modül bu bağlantıyı da kurar.

## 2.1 Secret

```bash
PW=$(aws secretsmanager get-random-password --password-length 32 --exclude-punctuation \
     --require-each-included-type --query RandomPassword --output text)
aws secretsmanager create-secret --region eu-central-1 --name dbws/redshift \
  --description "Redshift Serverless admin user for the Redshift Engine App" \
  --secret-string "{\"username\":\"dbwsadmin\",\"password\":\"$PW\"}"
echo "$PW"
```

Son satırdaki şifreyi 2.3'te kullanacaksınız.

## 2.2 DB security group

Name `dbws-sg-db-redshift`, VPC `dbws-vpc`. Inbound: **Redshift TCP 5439**, kaynak `dbws-sg-app-redshift`.

## 2.3 Namespace ve workgroup

**Amazon Redshift → Redshift Serverless → Create workgroup**

| Alan | Değer |
|---|---|
| Workgroup name | `dbws` |
| Base capacity | **8** RPU |
| VPC | `dbws-vpc` |
| Security groups | yalnızca `dbws-sg-db-redshift` |
| Subnets | `dbws-data-a`, `dbws-data-b`, `dbws-data-c` |
| Turn on enhanced VPC routing | **açık** |
| Publicly accessible | kapalı |
| Namespace | Create a new namespace: `dbws` |
| Database name | `dev` |
| Admin user credentials | **Customize admin user credentials** → Manually add the admin password. Kullanıcı `dbwsadmin`, şifre 2.1'deki şifre. |
| Encryption | AWS owned key |

Oluşturma 3-5 dakika sürer. **Workgroup → Endpoint** değerini port olmadan not alın:
`dbws.<ACCOUNT_ID>.eu-central-1.redshift-serverless.amazonaws.com`.

Zero-ETL, büyük ve küçük harf duyarlı adlar ister. CloudShell'de çalıştırın:

```bash
aws redshift-serverless update-workgroup --region eu-central-1 --workgroup-name dbws \
  --config-parameters parameterKey=enable_case_sensitive_identifier,parameterValue=true
```

## 2.4 Zero-ETL integration

Bu adım için Modül 1 (Aurora) tamamlanmış olmalı.

1. **Redshift → Redshift Serverless → Namespace `dbws` → Resource policy → Add authorized principals**:
   hesabınızı (`<ACCOUNT_ID>`) ekleyin. **Add authorized integration sources** bölümünde `dbws-aurora` cluster'ını seçin.
2. **RDS → Zero-ETL integrations → Create zero-ETL integration**:

| Alan | Değer |
|---|---|
| Integration name | `dbws-aurora-to-redshift` |
| Source | Aurora DB cluster `dbws-aurora` |
| Target | Redshift Serverless namespace `dbws` (bu hesap) |
| Data filtering options | `include: shop.*.*` |

Integration'ın durumu 15-30 dakikada **Active** olur.

## 2.5 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-redshift` |
| E2 role | `dbws-app-redshift-eu-central-1` |
| E3 | Subnet `dbws-app-c`, IP `10.20.12.12` |
| E4 | `dbws-tg-redshift`, health check `/redshift/health` |
| E5 | Path `/admin/reports`, `/redshift/*`, öncelik **20** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/redshift secret ARN>" },
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
  ]
}
```

`INTEGRATION_ARN` değerini **RDS → Zero-ETL integrations → dbws-aurora-to-redshift** ekranından alın.

```bash
ENGINE=redshift
URL_PREFIX=/redshift
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
DB_HOST=<workgroup endpoint>
DB_PORT=5439
DB_NAME=dev
DB_SECRET_ARN=<dbws/redshift secret ARN>
INTEGRATION_ARN=<zero-ETL integration ARN>
```

## 2.6 Doğrulama

1. Admin Console'da Redshift satırındaki **Seed** düğmesine basın. Bu, geçmiş satış tablosunu yazar.
2. Admin Console'da **Connect zero-ETL** düğmesine basın. Redshift, Aurora tablolarını `aurora_live` veritabanına kopyalamaya başlar.
3. `/admin/reports` sayfasını açın. **Group by** seçeneklerini değiştirin.
4. `/checkout` sayfasında bir sipariş verin. Rapor sayfasında **Live from Aurora (zero-ETL)** seçin ve **Refresh the status** düğmesine basın.
   "Newest workshop order" satırı, siparişinizin kaç saniye önce Redshift'e geldiğini gösterir.
