# Modül 10 - OpenSearch Service (Unstructured, Text search + Geospatial)

- **Sitedeki bölüm:** arama (`/search`), üst bardaki arama önerileri ve mağaza bulucu (`/stores`)
- **Bağlantı:** HTTPS 443, OpenSearch REST API, **IAM SigV4**. Fine-grained access control açıktır, master user Engine App'in IAM rolüdür.
- **Neden OpenSearch?** Kullanıcılar yazım hatası yapar ve Türkçe karakterleri atlar. OpenSearch metni parçalar, sonuçları alakaya göre
  sıralar ve coğrafi mesafe sorgularını destekler.

> CloudSearch yeni müşterilere kapalıdır. İnfografikte Geospatial altında Keyspaces geçer, ama Keyspaces'te coğrafi sorgu yoktur.
> Workshop, OpenSearch'ün `geo_point` alanını kullanır.

## 10.1 Önce IAM rolü

Domain, bu rolü master user olarak ister. Bu yüzden Modül 0'daki **E2** adımını şimdi yapın:
role `dbws-app-opensearch-eu-central-1`, inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["es:ESHttpGet", "es:ESHttpHead", "es:ESHttpPost", "es:ESHttpPut", "es:ESHttpDelete"],
      "Resource": "arn:aws:es:eu-central-1:<ACCOUNT_ID>:domain/dbws-search/*" },
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
  ]
}
```

Rol ARN'ini not alın: `arn:aws:iam::<ACCOUNT_ID>:role/dbws-app-opensearch-eu-central-1`.

## 10.2 DB security group

Name `dbws-sg-db-opensearch`. Inbound: **HTTPS TCP 443**, kaynak `dbws-sg-app-opensearch`. Önce Modül 0'daki **E1** adımını yapın.

## 10.3 Domain

**Amazon OpenSearch Service → Domains → Create domain → Standard create**

| Alan | Değer |
|---|---|
| Domain name | `dbws-search` |
| Template | Production |
| Deployment option | Domain with standby **kapalı**, 3-AZ |
| Engine version | OpenSearch **3.5** |
| Data nodes | `r6g.large.search`, **3** node, EBS gp3 20 GiB |
| Dedicated master nodes | açık, `m6g.large.search`, **3** node |
| Network | **VPC access**: `dbws-vpc`, subnet'ler `dbws-data-a/b/c`, security group yalnızca `dbws-sg-db-opensearch` |
| Fine-grained access control | açık → **Set IAM ARN as master user** → 10.1'deki rol ARN'i |
| Access policy | **Configure domain level access policy** → aşağıdaki JSON |
| Encryption | Require HTTPS, node-to-node encryption ve encryption at rest açık. TLS policy `Policy-Min-TLS-1-2-PFS-2023-10`. |

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

Hesaptaki ilk VPC domain'iyse konsol `AWSServiceRoleForAmazonOpenSearchService` adlı service-linked role'ü kendisi oluşturur.
Oluşturma 20-30 dakika sürer. **VPC endpoint** değerini https:// olmadan not alın: `vpc-dbws-search-xxxx.eu-central-1.es.amazonaws.com`.

## 10.4 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-opensearch` (10.2'de yapıldı) |
| E2 | 10.1'de yapıldı |
| E3 | Subnet `dbws-app-c`, IP `10.20.12.11` |
| E4 | `dbws-tg-opensearch`, health check `/opensearch/health` |
| E5 | Path `/search`, `/stores`, `/opensearch/*`, öncelik **100** |

```bash
ENGINE=opensearch
URL_PREFIX=/opensearch
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
OS_HOST=<VPC endpoint>
```

## 10.5 Doğrulama

1. Admin Console'da OpenSearch satırındaki **Seed** düğmesine basın. `products` ve `stores` indeksleri oluşur.
2. `/search` sayfasında **kulaklk (typo)** örneğine tıklayın. Yazım hatasına rağmen kulaklıklar bulunur.
3. **Exact words** seçin ve aynı aramayı yapın. Bu kez sonuç çıkmaz.
4. **standard** analyzer'ı seçin ve "kablosuz kulaklik" arayın. `tr_folded` analyzer'ı ı harfini i'ye çevirdiği için daha çok sonuç bulur.
5. `/stores` sayfasında haritaya tıklayın. Seçtiğiniz yarıçap içindeki mağazalar en yakından uzağa sıralanır.
