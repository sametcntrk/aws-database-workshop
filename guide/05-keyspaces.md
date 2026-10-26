# Modül 5 - Amazon Keyspaces (Semi-structured, Wide column)

- **Sitedeki bölüm:** aktivite geçmişi (`/account/activity`) ve ürün sayfalarındaki "Recently viewed" şeridi
- **Bağlantı:** CQL native protokolü, TCP 9142, TLS, IAM SigV4 (şifre yok). Trafik Keyspaces interface endpoint'inden geçer.
- **Neden Keyspaces?** Her görüntüleme ve satın alma bir olaydır. Olay sayısı çok yüksektir ve hep aynı anahtarla okunur:
  "bu ziyaretçinin son olayları". Keyspaces bu olayları ziyaretçiye göre gruplar ve zamana göre sıralı saklar.

## 5.1 Keyspace ve tablo

**Amazon Keyspaces → Keyspaces → Create keyspace**: Keyspace name `dbws`, Replication: Single-Region.

**Tables → Create table**

| Alan | Değer |
|---|---|
| Keyspace | `dbws` |
| Table name | `activity_by_user` |
| Columns | `user_id` text, `event_time` timestamp, `event_id` uuid, `event_type` text, `product_id` text, `detail` text |
| Partition key | `user_id` |
| Clustering columns | `event_time` **DESC**, `event_id` ASC |
| Capacity mode | On-demand |
| Point-in-time recovery | açık |
| Time to Live | açık, varsayılan süre **604800 saniye** (7 gün) |

Aynı tabloyu CQL editor ile de oluşturabilirsiniz:

```sql
CREATE TABLE dbws.activity_by_user (
  user_id text, event_time timestamp, event_id uuid,
  event_type text, product_id text, detail text,
  PRIMARY KEY ((user_id), event_time, event_id)
) WITH CLUSTERING ORDER BY (event_time DESC, event_id ASC)
  AND default_time_to_live = 604800
  AND CUSTOM_PROPERTIES = {'ttl': {'status': 'enabled'}};
```

## 5.2 Engine App

DB security group yoktur. Trafik Modül 0'daki `dbws-vpce-keyspaces` endpoint'inden geçer. `dbws-sg-vpce` grubu 9142 portuna izin verir.

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-keyspaces` |
| E2 role | `dbws-app-keyspaces-eu-central-1` |
| E3 | Subnet `dbws-app-a`, IP `10.20.10.13` |
| E4 | `dbws-tg-keyspaces`, health check `/keyspaces/health` |
| E5 | Path `/account/activity`, `/keyspaces/*`, öncelik **50** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["cassandra:Select", "cassandra:Modify"],
      "Resource": ["arn:aws:cassandra:eu-central-1:<ACCOUNT_ID>:/keyspace/dbws/",
                   "arn:aws:cassandra:eu-central-1:<ACCOUNT_ID>:/keyspace/dbws/table/activity_by_user"] },
    { "Effect": "Allow", "Action": "cassandra:Select",
      "Resource": "arn:aws:cassandra:eu-central-1:<ACCOUNT_ID>:/keyspace/system*" },
    { "Effect": "Allow", "Action": ["ec2:DescribeNetworkInterfaces", "ec2:DescribeVpcEndpoints"], "Resource": "*" },
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
  ]
}
```

`ec2:Describe...` izinleri, sürücünün VPC endpoint üzerinden bağlanırken `system.peers` tablosunu doldurabilmesi içindir.

```bash
ENGINE=keyspaces
URL_PREFIX=/keyspaces
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
KEYSPACE=dbws
TABLE_NAME=activity_by_user
```

## 5.3 Doğrulama

1. Admin Console'da Keyspaces satırındaki **Seed** düğmesine basın. Persona'ların geçmiş olayları yazılır.
2. Birkaç ürün sayfası açın, sonra `/account/activity` sayfasına gelin. Gezdiğiniz ürünler en yeniden en eskiye sıralı görünür.
3. **My persona (seeded)** seçin. Persona'nızın geçmişini görün.
4. **LOCAL_ONE** seçin. Bu okuma üç kopyadan yalnızca birini okur ve yarı maliyetlidir.
5. **Start the burst** düğmesine basın. Yeni bir on-demand tablo kapasitesini adım adım artırır.
   Bu yüzden bazı yazmalar geri çekilerek yeniden denenir. Panelde kaç yazmanın yeniden denendiğini görün.
