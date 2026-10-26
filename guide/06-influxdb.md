# Modül 6 - Timestream for InfluxDB (Semi-structured · Time-series)

**Domain dilimi:** depo sensör ve metrik verisi. **Read:** Flux `aggregateWindow(every: 1h, fn: mean)`, depo başına saatlik ortalama sıcaklık.
**Bağlantı:** HTTPS 8086, InfluxDB v2 API, kullanıcı adı/şifre (`dbws/influxdb` secret'ı).

> Timestream for LiveAnalytics yeni müşterilere kapalıdır; workshop yönetilen InfluxDB'yi kullanır.

## 6.1 Secret

```bash
PW=$(aws secretsmanager get-random-password --password-length 32 --exclude-punctuation \
     --require-each-included-type --query RandomPassword --output text)
aws secretsmanager create-secret --region eu-central-1 --name dbws/influxdb \
  --description "InfluxDB admin user for the InfluxDB Engine App" \
  --secret-string "{\"username\":\"dbwsadmin\",\"password\":\"$PW\"}"
echo "$PW"
```

## 6.2 DB security group

Name `dbws-sg-db-influxdb`, Inbound: **TCP 8086**, Source `dbws-sg-app-influxdb`.

## 6.3 InfluxDB instance

**Amazon Timestream → InfluxDB databases → Create InfluxDB database**

| Alan | Değer |
|---|---|
| DB identifier | `dbws-influxdb` |
| Username / Password | `dbwsadmin` / 6.1'deki şifre |
| Organization name | `dbws` |
| Bucket name | `metrics` |
| DB instance class | `db.influx.medium` |
| Storage type | Influx IO Included (3K IOPS) |
| Allocated storage | 20 GiB |
| Deployment settings | **Multi-AZ DB instance (standby)** |
| VPC / Subnets | `dbws-vpc`, `dbws-data-a`, `dbws-data-b`, `dbws-data-c` |
| Security groups | sadece `dbws-sg-db-influxdb` |
| Public access | Not publicly accessible |

Oluşturma 15-20 dk. **Endpoint**'i not alın: `xxxx.eu-central-1.timestream-influxdb.amazonaws.com`.

## 6.4 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-influxdb` |
| E2 role | `dbws-app-influxdb-eu-central-1` |
| E3 | Subnet `dbws-app-c`, IP `10.20.12.13` |
| E4 | `dbws-tg-influxdb`, health check `/influxdb/health` |
| E5 | Path `/influxdb`, `/influxdb/*`, öncelik **60** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/influxdb secret ARN>" }
  ]
}
```

```bash
ENGINE=influxdb
URL_PREFIX=/influxdb
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
INFLUX_URL=https://<InfluxDB endpoint>:8086
INFLUX_ORG=dbws
INFLUX_BUCKET=metrics
INFLUX_SECRET_ARN=<dbws/influxdb secret ARN>
```

## 6.5 Doğrulama

`/influxdb/` → **Seed** (4 depo × 2 sensör, 5 dakikada bir ölçüm) → **Read** (saatlik ortalama).
SQL'de aynı sonuç için `date_trunc` ve `GROUP BY` gerekirdi; Flux'ta tek satır `aggregateWindow`.
