# Modül 6 - Timestream for InfluxDB (Semi-structured, Time-series)

- **Sitedeki bölüm:** operasyon ekranı (`/admin/ops`) ve her siparişte yazılan sipariş sayacı
- **Bağlantı:** HTTPS 8086, InfluxDB v2 API. Kullanıcı adı ve şifre `dbws/influxdb` secret'ındadır.
- **Neden InfluxDB?** Sensör ve metrik verisi zaman damgalı noktalardan oluşur. InfluxDB bu noktaları zamana göre saklar ve
  "saatlik ortalama" gibi pencere hesaplarını tek satırla yapar.

> Timestream for LiveAnalytics yeni müşterilere kapalıdır. Workshop, yönetilen InfluxDB'yi kullanır.

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

Name `dbws-sg-db-influxdb`. Inbound: **TCP 8086**, kaynak `dbws-sg-app-influxdb`.

## 6.3 InfluxDB instance

**Amazon Timestream → InfluxDB databases → Create InfluxDB database**

| Alan | Değer |
|---|---|
| DB identifier | `dbws-influxdb` |
| Username ve password | `dbwsadmin` ve 6.1'deki şifre |
| Organization name | `dbws` |
| Bucket name | `metrics` |
| DB instance class | `db.influx.medium` |
| Storage type | Influx IO Included (3K IOPS) |
| Allocated storage | 20 GiB |
| Deployment settings | **Multi-AZ DB instance (standby)** |
| VPC ve subnet'ler | `dbws-vpc`, `dbws-data-a`, `dbws-data-b`, `dbws-data-c` |
| Security groups | yalnızca `dbws-sg-db-influxdb` |
| Public access | Not publicly accessible |

Oluşturma 15-20 dakika sürer. **Endpoint** değerini not alın: `xxxx.eu-central-1.timestream-influxdb.amazonaws.com`.

## 6.4 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-influxdb` |
| E2 role | `dbws-app-influxdb-eu-central-1` |
| E3 | Subnet `dbws-app-c`, IP `10.20.12.13` |
| E4 | `dbws-tg-influxdb`, health check `/influxdb/health` |
| E5 | Path `/admin/ops`, `/influxdb/*`, öncelik **60** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/influxdb secret ARN>" },
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
  ]
}
```

```bash
ENGINE=influxdb
URL_PREFIX=/influxdb
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
INFLUX_URL=https://<InfluxDB endpoint>:8086
INFLUX_ORG=dbws
INFLUX_BUCKET=metrics
INFLUX_SECRET_ARN=<dbws/influxdb secret ARN>
```

## 6.5 Doğrulama

1. Admin Console'da InfluxDB satırındaki **Seed** düğmesine basın. Depo sensörleri ve son 24 saatin dakikalık sipariş sayıları yazılır.
2. `/admin/ops` sayfasını açın. **Window** seçeneğini 1 dakikadan 1 saate çevirin.
   Aynı zaman aralığı için daha az nokta döndüğünü paneldeki sonuç sayısından görün.
3. Bir sipariş verin ve sipariş grafiğinin son dakikasına bakın.
