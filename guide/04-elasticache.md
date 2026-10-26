# Modül 4 - ElastiCache Serverless Valkey (Semi-structured, In-memory)

- **Sitedeki bölüm:** flaş indirim (`/deals`), canlı liderlik tablosu (`/admin/live`) ve her sayfadaki oturum kaydı
- **Bağlantı:** RESP protokolü, TCP 6379 (okuma için 6380), TLS. ACL kullanıcısı `dbws-app`, şifresi `dbws/elasticache` secret'ında.
- **Neden ElastiCache?** Veri bellekte durur ve komutlar mikrosaniyeler sürer. Sayaçlar ve sıralı listeler gibi canlı veriler için uygundur.

## 4.1 Secret

```bash
PW=$(aws secretsmanager get-random-password --password-length 32 --exclude-punctuation \
     --require-each-included-type --query RandomPassword --output text)
aws secretsmanager create-secret --region eu-central-1 --name dbws/elasticache \
  --description "ElastiCache user for the ElastiCache Engine App" \
  --secret-string "{\"username\":\"dbws-app\",\"password\":\"$PW\"}"
echo "$PW"
```

## 4.2 Kullanıcı ve kullanıcı grubu

**ElastiCache → User management → Users → Create user**

| Alan | Değer |
|---|---|
| User ID ve User name | `dbws-app` |
| Engine | **Valkey** |
| Authentication mode | Password: 4.1'deki şifre |
| Access string | `on ~* +@all -@dangerous` |

**User groups → Create user group**: User group ID `dbws-users`, Engine **Valkey**, Users: `dbws-app`.

> Valkey'de "default" adlı bir kullanıcı zorunlu değildir. Valkey, şifresiz kullanıcıya izin vermez.

## 4.3 DB security group

Name `dbws-sg-db-elasticache`. Inbound: **TCP 6379** ve **TCP 6380**, kaynak `dbws-sg-app-elasticache`.

## 4.4 Serverless cache

**ElastiCache → Valkey caches → Create Valkey cache → Serverless → Customize default settings**

| Alan | Değer |
|---|---|
| Name | `dbws-cache` |
| Engine version | 8 |
| VPC ve subnet'ler | `dbws-vpc`, `dbws-data-a`, `dbws-data-b`, `dbws-data-c` |
| Security groups | yalnızca `dbws-sg-db-elasticache` |
| Access control | **User group access control list** → `dbws-users` |

Oluşturma 3-5 dakika sürer. **Endpoint** değerini not alın (port 6379).

## 4.5 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-elasticache` |
| E2 role | `dbws-app-elasticache-eu-central-1` |
| E3 | Subnet `dbws-app-b`, IP `10.20.11.13` |
| E4 | `dbws-tg-elasticache`, health check `/elasticache/health` |
| E5 | Path `/deals`, `/admin/live`, `/elasticache/*`, öncelik **40** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/elasticache secret ARN>" },
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
  ]
}
```

```bash
ENGINE=elasticache
URL_PREFIX=/elasticache
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
CACHE_HOST=<cache endpoint>
CACHE_PORT=6379
CACHE_SECRET_ARN=<dbws/elasticache secret ARN>
```

## 4.6 Doğrulama

1. Admin Console'da ElastiCache satırındaki **Seed** düğmesine basın. Liderlik tablosu dolar ve 50 adetlik flaş indirim başlar.
2. `/deals` sayfasında **Buy one now** düğmesine basın. Panelde `DECR` komutunu görün.
3. **Start the rush** düğmesine önce **Atomic DECR**, sonra **Read, then write** seçiliyken basın.
   İkinci yöntemde mağaza, elinde olmayan ürünleri de satar. Bu bir yarış durumudur (race condition).
4. Oturum bölümünde TTL'i 30 saniye yapın ve oturumu okuyun. TTL değeri azalır, sıfırda oturum silinir.
5. `/admin/live` sayfasını açık bırakın ve başka bir sekmede sipariş verin. Persona'nız 5 saniye içinde tabloda yükselir.
