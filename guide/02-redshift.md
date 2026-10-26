# Modül 2 - Redshift Serverless (Structured · Columnar)

**Domain dilimi:** satış analitiği. **Read:** ay ve kategoriye göre `GROUP BY` / `SUM`.
**Bağlantı:** PostgreSQL wire protokolü, TCP 5439, TLS, kullanıcı adı/şifre (`dbws/redshift` secret'ı).

## 2.1 Secret

**CloudShell** (konsolun üst çubuğu) ile güçlü bir şifre üretip secret'ı oluşturun:

```bash
PW=$(aws secretsmanager get-random-password --password-length 32 --exclude-punctuation \
     --require-each-included-type --query RandomPassword --output text)
aws secretsmanager create-secret --region eu-central-1 --name dbws/redshift \
  --description "Redshift Serverless admin user for the Redshift Engine App" \
  --secret-string "{\"username\":\"dbwsadmin\",\"password\":\"$PW\"}"
echo "$PW"   # 2.3'te admin şifresi olarak yapıştırın
```

Konsol alternatifi: **Secrets Manager → Store a new secret → Other type of secret**, key/value `username` = `dbwsadmin`, `password` = (büyük harf, küçük harf ve rakam içeren 32 karakter), Secret name `dbws/redshift`.
Secret ARN'ini not alın.

## 2.2 DB security group

Name `dbws-sg-db-redshift`, VPC `dbws-vpc`, Inbound: **Redshift TCP 5439**, Source `dbws-sg-app-redshift`.

## 2.3 Namespace ve workgroup

**Amazon Redshift → Redshift Serverless → Create workgroup**

| Alan | Değer |
|---|---|
| Workgroup name | `dbws` |
| Base capacity | **8** RPU |
| VPC | `dbws-vpc` |
| Security groups | sadece `dbws-sg-db-redshift` |
| Subnets | `dbws-data-a`, `dbws-data-b`, `dbws-data-c` |
| Turn on enhanced VPC routing | **açık** |
| Publicly accessible | kapalı |
| Namespace | Create a new namespace: `dbws` |
| Database name | `dev` |
| Admin user credentials | **Customize admin user credentials** → Manually add the admin password: kullanıcı `dbwsadmin`, şifre = 2.1'deki şifre |
| Permissions | IAM rolü gerekmez |
| Encryption | AWS owned key |

Oluşturma 3-5 dk. **Workgroup → Endpoint**'i not alın: `dbws.<ACCOUNT_ID>.eu-central-1.redshift-serverless.amazonaws.com` (port 5439 olmadan).

> Enhanced VPC routing açıkken Redshift Serverless 3 farklı AZ'de subnet ister; ağın 3 AZ olmasının sebebi budur.

## 2.4 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-redshift` |
| E2 role | `dbws-app-redshift-eu-central-1` |
| E3 | Subnet `dbws-app-c`, IP `10.20.12.12` |
| E4 | `dbws-tg-redshift`, health check `/redshift/health` |
| E5 | Path `/redshift`, `/redshift/*`, öncelik **20** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/redshift secret ARN>" }
  ]
}
```

```bash
ENGINE=redshift
URL_PREFIX=/redshift
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
DB_HOST=<workgroup endpoint>
DB_PORT=5439
DB_NAME=dev
DB_SECRET_ARN=<dbws/redshift secret ARN>
```

## 2.5 Doğrulama

`/redshift/` → **Seed** (`sales` tablosu, DISTKEY `customer_id`, SORTKEY `order_date`) → **Read** (aylık kategori geliri).
Redshift Query Editor v2'de aynı sorguyu çalıştırıp **Query profile**'da sadece seçilen sütunların okunduğunu görün.
