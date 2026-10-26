# Modül 4 - ElastiCache Serverless Valkey (Semi-structured · In-memory)

**Domain dilimi:** oturumlar ve liderlik tablosu. **Read:** `ZREVRANGE ... 0 9 WITHSCORES` ve TTL'li oturum hash'i.
**Bağlantı:** RESP protokolü, TCP 6379 (okuma için 6380), TLS, ACL kullanıcısı `dbws-app` (şifre `dbws/elasticache` secret'ında).

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
| User ID | `dbws-app` |
| User name | `dbws-app` |
| Engine | **Valkey** |
| Authentication mode | Password: 4.1'deki şifre |
| Access string | `on ~* +@all -@dangerous` |

**User groups → Create user group**: User group ID `dbws-users`, Engine **Valkey**, Users: `dbws-app`.

> Valkey'de "default" kullanıcı zorunlu değildir ve şifresiz kullanıcıya izin verilmez.

## 4.3 DB security group

Name `dbws-sg-db-elasticache`, Inbound: **TCP 6379** ve **TCP 6380**, Source `dbws-sg-app-elasticache`.

## 4.4 Serverless cache

**ElastiCache → Valkey caches → Create Valkey cache → Serverless → Customize default settings**

| Alan | Değer |
|---|---|
| Name | `dbws-cache` |
| Engine version | 8 |
| VPC / Subnets | `dbws-vpc`, `dbws-data-a`, `dbws-data-b`, `dbws-data-c` |
| Security groups | sadece `dbws-sg-db-elasticache` |
| Access control | **User group access control list** → `dbws-users` |
| Encryption | in transit zorunlu (Serverless'ta her zaman açık) |

Oluşturma 3-5 dk. **Endpoint**'i not alın (`dbws-cache-xxxx.serverless.euc1.cache.amazonaws.com`, port 6379).

## 4.5 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-elasticache` |
| E2 role | `dbws-app-elasticache-eu-central-1` |
| E3 | Subnet `dbws-app-b`, IP `10.20.11.13` |
| E4 | `dbws-tg-elasticache`, health check `/elasticache/health` |
| E5 | Path `/elasticache`, `/elasticache/*`, öncelik **40** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/elasticache secret ARN>" }
  ]
}
```

```bash
ENGINE=elasticache
URL_PREFIX=/elasticache
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
CACHE_HOST=<cache endpoint>
CACHE_PORT=6379
CACHE_SECRET_ARN=<dbws/elasticache secret ARN>
```

## 4.6 Doğrulama

`/elasticache/` → **Seed** → **Read**. Read'i birkaç dakika arayla tekrarlayın: oturumun kalan TTL'i azalır; 1 saat sonra oturum kendiliğinden silinir.
