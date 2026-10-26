# Modül 8 - Amazon DocumentDB (Semi-structured, Document)

**İlk bu modülü yapın.** Sitenin ana sayfası, kategori sayfaları, ürün sayfaları ve Admin Console bu Engine App'tedir.

- **Sitedeki bölüm:** ürün kataloğu (`/`, `/c/<kategori>`, `/p/<ürün>`) ve Admin Console (`/admin`)
- **Bağlantı:** MongoDB wire protokolü, TCP 27017, TLS. Kullanıcı adı ve şifre `dbws/docdb` secret'ındadır.
- **Neden DocumentDB?** Her ürün tek bir JSON dokümandır. Dokümanların alanları farklı olabilir ve iç içe alanlar tek okumada gelir.

## 8.1 Secret

CloudShell'de çalıştırın:

```bash
PW=$(aws secretsmanager get-random-password --password-length 32 --exclude-punctuation \
     --require-each-included-type --query RandomPassword --output text)
aws secretsmanager create-secret --region eu-central-1 --name dbws/docdb \
  --description "DocumentDB admin user for the DocumentDB Engine App" \
  --secret-string "{\"username\":\"dbwsadmin\",\"password\":\"$PW\"}"
echo "$PW"
```

Son satırdaki şifreyi 8.3'te kullanacaksınız. Secret ARN'ini not alın.

## 8.2 DB security group ve subnet group

- Security group: Name `dbws-sg-db-docdb`, VPC `dbws-vpc`. Inbound: **TCP 27017**, kaynak `dbws-sg-app-docdb`.
  `dbws-sg-app-docdb` henüz yoksa önce Modül 0'daki **E1** adımını yapın.
- **DocumentDB → Subnet groups → Create**: Name `dbws-docdb`, VPC `dbws-vpc`, subnet'ler `dbws-data-a/b/c`.

## 8.3 Cluster

**Amazon DocumentDB → Clusters → Create → Instance-based cluster**

| Alan | Değer |
|---|---|
| Cluster identifier | `dbws-docdb` |
| Engine version | **8.0.0** |
| Instance class | `db.r6g.large` |
| Number of instances | **2** |
| Username ve password | `dbwsadmin` ve 8.1'deki şifre (Self managed) |
| Show advanced settings → VPC ve subnet group | `dbws-vpc` ve `dbws-docdb` |
| Security groups | yalnızca `dbws-sg-db-docdb` |
| Encryption | açık. Backup retention 1 day. Deletion protection kapalı. |

İsterseniz instance'ları `dbws-docdb-1` (AZ b) ve `dbws-docdb-2` (AZ c) olarak adlandırın.
Oluşturma 10-15 dakika sürer. **Cluster endpoint** değerini not alın: `dbws-docdb.cluster-xxxx.eu-central-1.docdb.amazonaws.com`.

## 8.4 Engine App

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-docdb` |
| E2 role | `dbws-app-docdb-eu-central-1` |
| E3 | Subnet `dbws-app-b`, IP `10.20.11.12` |
| E4 | `dbws-tg-docdb`, health check `/docdb/health` |
| E5 | Path `/docdb/*`, öncelik **80** |

E2 inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/docdb secret ARN>" },
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
  ]
}
```

E3 user data, engine satırları:

```bash
ENGINE=docdb
URL_PREFIX=/docdb
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
DB_HOST=<cluster endpoint>
DB_PORT=27017
DB_SECRET_ARN=<dbws/docdb secret ARN>
```

**Ek adım:** ALB'nin varsayılan kuralını DocumentDB App'e yönlendirin. Böylece `/` ve bilinmeyen bütün yollar mağazayı açar.
**EC2 → Load Balancers → dbws-alb → Listeners → HTTPS:443 → Default rule → Edit**:
Action **Forward to target groups** → `dbws-tg-docdb`.

## 8.5 Admin Console ve ilk veri yükleme

1. CloudShell ile yönetici anahtarını okuyun:
   `aws secretsmanager get-secret-value --secret-id dbws/admin --query SecretString --output text`
2. `https://dbworkshop.tdsynnexlab.link/admin` adresini açın.
3. Anahtarı **Admin key** alanına yazın ve **Save the key in this browser** düğmesine basın.
4. DocumentDB satırındaki **Seed** düğmesine basın. 200 ürün yazılır ve indeksler oluşur.

Diğer engine'leri kurdukça her biri için aynı satırdaki **Seed** düğmesine basın.
Bütün engine'ler hazırsa **Seed all Engines** düğmesi hepsini sırayla yükler.

## 8.6 Doğrulama

1. `https://dbworkshop.tdsynnexlab.link/` adresini açın. İlk ziyarette bir **persona** seçin.
2. Ana sayfada kategoriler ve en yüksek puanlı ürünler görünmeli.
3. Sağdaki **Behind the scenes** panelinde `aggregate` ve `find` çağrılarını bulun.
4. Bir kategoriye girin. **Experiment** kutusunda **Collection scan** seçeneğini seçin.
   Paneldeki "docs examined" değerinin, indeksli okumaya göre büyüdüğünü görün.

Diğer engine'ler henüz kurulmadıysa sayfanın bazı parçaları (görseller, öneriler, flaş indirim) boş kalır. Bu beklenen bir durumdur.
