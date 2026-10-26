# Modül 10 - OpenSearch Service (Unstructured · Text search + Geospatial)

**Domain dilimi:** ürün arama ve mağaza konumları. **Read:** yazım hatasına toleranslı `multi_match` (fuzziness) ve `geo_distance` (İstanbul'a 25 km).
**Bağlantı:** HTTPS 443, OpenSearch REST API, **IAM SigV4** (fine-grained access control, master user = Engine App rolü).

> CloudSearch yeni müşterilere kapalıdır. İnfografikte Geospatial altında Keyspaces geçer ama Keyspaces'te coğrafi sorgu yoktur; workshop OpenSearch `geo_point` kullanır.

## 10.1 Önce IAM rolü (domain bu rolü master user olarak ister)

Modül 0 → **E2**'yi şimdi yapın: role `dbws-app-opensearch-eu-central-1`, inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["es:ESHttpGet", "es:ESHttpHead", "es:ESHttpPost", "es:ESHttpPut", "es:ESHttpDelete"],
      "Resource": "arn:aws:es:eu-central-1:<ACCOUNT_ID>:domain/dbws-search/*" }
  ]
}
```

Rol ARN'ini not alın: `arn:aws:iam::<ACCOUNT_ID>:role/dbws-app-opensearch-eu-central-1`.

## 10.2 DB security group

Name `dbws-sg-db-opensearch`, Inbound: **HTTPS TCP 443**, Source `dbws-sg-app-opensearch` (önce Modül 0 → **E1**).

## 10.3 Domain

**Amazon OpenSearch Service → Domains → Create domain → Standard create**

| Alan | Değer |
|---|---|
| Domain name | `dbws-search` |
| Template | Production |
| Deployment option | **Domain with standby kapalı**, 3-AZ |
| Engine version | OpenSearch **3.5** |
| Data nodes | `r6g.large.search`, **3** node, EBS gp3 20 GiB |
| Dedicated master nodes | açık, `m6g.large.search`, **3** node |
| Network | **VPC access**: `dbws-vpc`, subnet'ler `dbws-data-a/b/c`, security group sadece `dbws-sg-db-opensearch` |
| Fine-grained access control | açık → **Set IAM ARN as master user** → 10.1'deki rol ARN'i |
| Access policy | **Configure domain level access policy** → JSON aşağıda |
| Encryption | Require HTTPS, node-to-node encryption, encryption at rest: hepsi açık; TLS policy `Policy-Min-TLS-1-2-PFS-2023-10` |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<ACCOUNT_ID>:role/dbws-app-opensearch-eu-central-1" },
      "Action": "es:ESHttp*",
      "Resource": "arn:aws:es:eu-central-1:<ACCOUNT_ID>:domain/dbws-search/*" }
  ]
}
```

Hesapta ilk VPC domain'iyse konsol `AWSServiceRoleForAmazonOpenSearchService` service-linked role'ünü kendisi oluşturur.
Oluşturma 20-30 dk. **VPC endpoint**'i not alın: `vpc-dbws-search-xxxx.eu-central-1.es.amazonaws.com` (https:// olmadan).

## 10.4 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-opensearch` (10.2'de yapıldı) |
| E2 | 10.1'de yapıldı |
| E3 | Subnet `dbws-app-c`, IP `10.20.12.11` |
| E4 | `dbws-tg-opensearch`, health check `/opensearch/health` |
| E5 | Path `/opensearch`, `/opensearch/*`, öncelik **100** |

```bash
ENGINE=opensearch
URL_PREFIX=/opensearch
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
OS_HOST=<VPC endpoint>
```

## 10.5 Doğrulama

`/opensearch/` → **Seed** (`products` indeksi `tr_folded` analyzer ile: Türkçe küçük harf + ASCII katlama; `stores` indeksi `geo_point` ile) → **Read**.
"kablosuz kulaklik" (ı yerine i) aramasının yine de doğru ürünleri bulduğunu ve mağazaların uzaklığa göre sıralandığını görün.
