# Modül 5 - Amazon Keyspaces (Semi-structured · Wide column)

**Domain dilimi:** kullanıcı aktivite akışı. **Read:** bir kullanıcının son 20 olayı (`WHERE user_id = 'C00001' LIMIT 20`).
**Bağlantı:** CQL native protokolü, TCP 9142, TLS, IAM SigV4 (şifre yok), **Keyspaces interface endpoint** üzerinden.

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

Aynı tablo CQL ile (CQL editor):

```sql
CREATE TABLE dbws.activity_by_user (
  user_id text, event_time timestamp, event_id uuid,
  event_type text, product_id text, detail text,
  PRIMARY KEY ((user_id), event_time, event_id)
) WITH CLUSTERING ORDER BY (event_time DESC, event_id ASC);
```

## 5.2 Engine App

DB security group yok. Trafik Modül 0'daki `dbws-vpce-keyspaces` endpoint'inden geçer (`dbws-sg-vpce` 9142'ye izin verir).

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-keyspaces` |
| E2 role | `dbws-app-keyspaces-eu-central-1` |
| E3 | Subnet `dbws-app-a`, IP `10.20.10.13` |
| E4 | `dbws-tg-keyspaces`, health check `/keyspaces/health` |
| E5 | Path `/keyspaces`, `/keyspaces/*`, öncelik **50** |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["cassandra:Select", "cassandra:Modify"],
      "Resource": ["arn:aws:cassandra:eu-central-1:<ACCOUNT_ID>:/keyspace/dbws/",
                   "arn:aws:cassandra:eu-central-1:<ACCOUNT_ID>:/keyspace/dbws/table/activity_by_user"] },
    { "Effect": "Allow", "Action": "cassandra:Select",
      "Resource": "arn:aws:cassandra:eu-central-1:<ACCOUNT_ID>:/keyspace/system*" },
    { "Effect": "Allow", "Action": ["ec2:DescribeNetworkInterfaces", "ec2:DescribeVpcEndpoints"], "Resource": "*" }
  ]
}
```

Son iki izin, sürücünün VPC endpoint üzerinden bağlanırken `system.peers` tablosunu doldurabilmesi içindir.

```bash
ENGINE=keyspaces
URL_PREFIX=/keyspaces
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
KEYSPACE=dbws
TABLE_NAME=activity_by_user
```

## 5.3 Doğrulama

`/keyspaces/` → **Seed** → **Read**. CQL editor'de `WHERE` olmadan `SELECT` deneyin; sonra partition anahtarıyla deneyin.
Keyspaces `TRUNCATE` desteklemez: Seed eski veriyi partition partition `DELETE` ile siler.
