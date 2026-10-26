# Modül 0 - Ortak altyapı

Bu modül bütün Engine'lerin kullandığı ağı, VPC endpoint'lerini, ALB'yi, sertifikayı ve DNS kaydını kurar.
Sonunda **Engine App deseni** bölümü var: her engine modülü bu deseni kendi değerleriyle tekrarlar.

Region: **eu-central-1**. Bütün kaynaklara `Name` etiketi verin (tablolardaki ad).

---

## 0.1 VPC

**VPC → Your VPCs → Create VPC**

| Alan | Değer |
|---|---|
| Resources to create | **VPC only** |
| Name tag | `dbws-vpc` |
| IPv4 CIDR | `10.20.0.0/16` |
| IPv6 | No IPv6 CIDR block |
| Tenancy | Default |

Oluşturduktan sonra **Actions → Edit VPC settings**: **Enable DNS resolution** ve **Enable DNS hostnames** işaretli olsun.
Interface endpoint'lerin private DNS'i ikisine de ihtiyaç duyar.

## 0.2 Internet gateway

**VPC → Internet gateways → Create internet gateway**: Name `dbws-igw`. Sonra **Actions → Attach to VPC → dbws-vpc**.

## 0.3 Subnet'ler (9 adet)

**VPC → Subnets → Create subnet**, VPC: `dbws-vpc`. Tek ekranda **Add new subnet** ile hepsini ekleyebilirsiniz.

| Name | Availability Zone | IPv4 CIDR |
|---|---|---|
| `dbws-public-a` | eu-central-1a | `10.20.0.0/24` |
| `dbws-public-b` | eu-central-1b | `10.20.1.0/24` |
| `dbws-public-c` | eu-central-1c | `10.20.2.0/24` |
| `dbws-app-a` | eu-central-1a | `10.20.10.0/24` |
| `dbws-app-b` | eu-central-1b | `10.20.11.0/24` |
| `dbws-app-c` | eu-central-1c | `10.20.12.0/24` |
| `dbws-data-a` | eu-central-1a | `10.20.20.0/24` |
| `dbws-data-b` | eu-central-1b | `10.20.21.0/24` |
| `dbws-data-c` | eu-central-1c | `10.20.22.0/24` |

Public subnet'lerde **Auto-assign public IPv4** kapalı kalsın: public IP'yi sadece ALB ve NAT gateway alır.

> Neden 3 AZ? Redshift Serverless, Enhanced VPC Routing açıkken 3 farklı AZ'de subnet ister. Bütün katmanlar aynı 3 AZ'yi kullanır.

## 0.4 NAT gateway'ler (her AZ'de bir tane)

**VPC → NAT gateways → Create NAT gateway**, üç kez:

| Name | Subnet | Connectivity type | Elastic IP |
|---|---|---|---|
| `dbws-nat-a` | `dbws-public-a` | Public | **Allocate Elastic IP** |
| `dbws-nat-b` | `dbws-public-b` | Public | **Allocate Elastic IP** |
| `dbws-nat-c` | `dbws-public-c` | Public | **Allocate Elastic IP** |

Durumları **Available** olana kadar (2-3 dk) bir sonraki adımı yapabilirsiniz.

## 0.5 Route table'lar (her subnet'e bir tane)

**VPC → Route tables → Create route table**, VPC `dbws-vpc`. Her tabloyu oluşturduktan sonra:
**Routes → Edit routes** ile route'u ekleyin, **Subnet associations → Edit subnet associations** ile subnet'i bağlayın.

| Route table | Ek route | Bağlı subnet |
|---|---|---|
| `dbws-rt-public-a` | `0.0.0.0/0` → Internet Gateway `dbws-igw` | `dbws-public-a` |
| `dbws-rt-public-b` | `0.0.0.0/0` → Internet Gateway `dbws-igw` | `dbws-public-b` |
| `dbws-rt-public-c` | `0.0.0.0/0` → Internet Gateway `dbws-igw` | `dbws-public-c` |
| `dbws-rt-app-a` | `0.0.0.0/0` → NAT Gateway `dbws-nat-a` | `dbws-app-a` |
| `dbws-rt-app-b` | `0.0.0.0/0` → NAT Gateway `dbws-nat-b` | `dbws-app-b` |
| `dbws-rt-app-c` | `0.0.0.0/0` → NAT Gateway `dbws-nat-c` | `dbws-app-c` |
| `dbws-rt-data-a` | (yok, sadece `local`) | `dbws-data-a` |
| `dbws-rt-data-b` | (yok, sadece `local`) | `dbws-data-b` |
| `dbws-rt-data-c` | (yok, sadece `local`) | `dbws-data-c` |

Her AZ kendi NAT gateway'ini kullanır: bir AZ kaybolursa diğer AZ'lerin çıkışı etkilenmez.
Data subnet'lerinin internete çıkışı yoktur.

## 0.6 Gateway endpoint'ler (S3 ve DynamoDB)

**VPC → Endpoints → Create endpoint**, iki kez:

| Alan | S3 | DynamoDB |
|---|---|---|
| Name | `dbws-vpce-s3` | `dbws-vpce-dynamodb` |
| Type | AWS services | AWS services |
| Service | `com.amazonaws.eu-central-1.s3`, Type **Gateway** | `com.amazonaws.eu-central-1.dynamodb`, Type **Gateway** |
| VPC | `dbws-vpc` | `dbws-vpc` |
| Route tables | `dbws-rt-app-a`, `dbws-rt-app-b`, `dbws-rt-app-c` | aynı üçü |
| Policy | Full access | Full access |

Sonuç: app route table'larına `pl-xxxx (S3)` ve `pl-xxxx (DynamoDB)` → `vpce-...` satırları eklenir. Bu servislere giden trafik NAT'a uğramaz.

## 0.7 Interface endpoint'ler

Önce security group: **EC2 → Security Groups → Create security group**

| Alan | Değer |
|---|---|
| Name | `dbws-sg-vpce` |
| Description | `Interface endpoints - HTTPS and Keyspaces (9142) from the app subnets` |
| VPC | `dbws-vpc` |
| Inbound | TCP 443 from `10.20.10.0/24`, `10.20.11.0/24`, `10.20.12.0/24`; TCP 9142 from aynı üç CIDR |
| Outbound | varsayılan (All traffic) |

Sonra **VPC → Endpoints → Create endpoint**, beş kez (Type: AWS services, Type **Interface**):

| Name | Service |
|---|---|
| `dbws-vpce-secretsmanager` | `com.amazonaws.eu-central-1.secretsmanager` |
| `dbws-vpce-keyspaces` | `com.amazonaws.eu-central-1.cassandra` |
| `dbws-vpce-ssm` | `com.amazonaws.eu-central-1.ssm` |
| `dbws-vpce-ssmmessages` | `com.amazonaws.eu-central-1.ssmmessages` |
| `dbws-vpce-ec2messages` | `com.amazonaws.eu-central-1.ec2messages` |

Her biri için: VPC `dbws-vpc`, **Enable DNS name** işaretli, Subnets: **data** subnet'leri (`dbws-data-a/b/c`, her AZ'de bir tane),
Security groups: `dbws-sg-vpce`, Policy: Full access.

> Endpoint ENI'leri data subnet'lerinde, kullanan Engine'lerin yanında durur. Engine App `secretsmanager.eu-central-1.amazonaws.com`
> adını çözdüğünde kendi AZ'sindeki ENI'nin private IP'sini alır.

## 0.8 ALB security group

**EC2 → Security Groups → Create security group**

| Alan | Değer |
|---|---|
| Name | `dbws-sg-alb` |
| Description | `ALB - HTTPS 443 and HTTP 80 (redirect) from AllowedCidr` |
| VPC | `dbws-vpc` |
| Inbound | TCP 443 from `0.0.0.0/0`; TCP 80 from `0.0.0.0/0` (workshop salonunun IP'sini biliyorsanız `x.x.x.x/32` yazın) |

## 0.9 Sertifika (ACM)

**Certificate Manager (eu-central-1) → Request → Request a public certificate**

| Alan | Değer |
|---|---|
| Fully qualified domain name | `dbworkshop.tdsynnexlab.link` |
| Validation method | DNS validation |
| Key algorithm | RSA 2048 |

Sertifikayı açın → **Create records in Route 53 → Create records**. Durum 2-5 dakikada **Issued** olur.

## 0.10 Application Load Balancer

**EC2 → Load Balancers → Create load balancer → Application Load Balancer**

| Alan | Değer |
|---|---|
| Name | `dbws-alb` |
| Scheme | Internet-facing |
| IP address type | IPv4 |
| VPC | `dbws-vpc` |
| Mappings | eu-central-1a `dbws-public-a`, eu-central-1b `dbws-public-b`, eu-central-1c `dbws-public-c` |
| Security groups | sadece `dbws-sg-alb` |

**Listener 1 - HTTPS : 443**

| Alan | Değer |
|---|---|
| Default action | **Return fixed response**: 200, Content type `text/html`, body aşağıda |
| Security policy | `ELBSecurityPolicy-TLS13-1-2-2021-06` |
| Default SSL/TLS certificate | From ACM: `dbworkshop.tdsynnexlab.link` |

Fixed response body (Dashboard, en fazla 1024 bayt):

```html
<html><head><meta charset="utf-8"><title>AWS Database Workshop</title> <style>body{font-family:sans-serif;margin:40px}a{display:block;margin:6px 0}</style></head> <body><h1>AWS Database Workshop</h1><p>Bir Engine App seçin:</p> <a href="/aurora/">Aurora PostgreSQL - Relational</a><a href="/redshift/">Redshift - Columnar</a> <a href="/dynamodb/">DynamoDB - Key-value</a><a href="/elasticache/">ElastiCache - In-memory</a> <a href="/keyspaces/">Keyspaces - Wide column</a><a href="/influxdb/">InfluxDB - Time-series</a> <a href="/neptune/">Neptune - Graph</a><a href="/docdb/">DocumentDB - Document</a> <a href="/s3/">S3 - Blob</a><a href="/opensearch/">OpenSearch - Text search + geo</a></body></html>
```

**Listener 2 - HTTP : 80**: Default action **Redirect to URL**, Protocol HTTPS, Port 443, Status code 301.

ALB oluştuktan sonra **Attributes → Edit**: **Drop invalid header fields** açık, **Connection idle timeout** `120` saniye.
(Büyük Seed işlemleri 60 saniyeyi geçebilir.)

## 0.11 DNS kaydı

**Route 53 → Hosted zones → tdsynnexlab.link → Create record**

| Alan | Değer |
|---|---|
| Record name | `dbworkshop` |
| Record type | A |
| Alias | açık → Alias to Application and Classic Load Balancer → Europe (Frankfurt) → `dbws-alb` |
| Evaluate target health | No |

Doğrulama: tarayıcıda `https://dbworkshop.tdsynnexlab.link/` Dashboard sayfasını göstermeli.
Linkler henüz 404/503 döner; her engine modülü bir linki çalışır hale getirir.

## 0.12 Launch template (bütün Engine App'ler için)

**EC2 → Launch Templates → Create launch template**

| Alan | Değer |
|---|---|
| Name | `dbws-engine-app` |
| AMI, instance type, key pair, network | boş bırakın (instance oluştururken seçilir) |
| Storage | Volume 1 (`/dev/xvda`): 20 GiB, **gp3**, Encrypted **Yes**, Delete on termination **Yes** |
| Advanced details → Metadata version | **V2 only (token required)** |
| Advanced details → Metadata response hop limit | `1` |
| Advanced details → Detailed CloudWatch monitoring | Enable |

EC2'lere SSH anahtarı ve public IP verilmez; bağlanmak için **Systems Manager → Session Manager** kullanılır (0.7'deki SSM endpoint'leri).

---

## Engine App deseni (her engine modülünde tekrarlanır)

Her engine modülü önce kendi Engine'ini kurar, sonra bu altı adımı **o modülün tablosundaki değerlerle** yapar.
Aşağıdaki `<engine>` yerine modülün kimliğini yazın (`aurora`, `redshift`, `dynamodb`, `elasticache`, `keyspaces`, `influxdb`, `neptune`, `docdb`, `s3`, `opensearch`).

### E1 - App security group

**EC2 → Security Groups → Create security group**

| Alan | Değer |
|---|---|
| Name | `dbws-sg-app-<engine>` |
| Description | `Engine App <Engine> - HTTP 8000 from the ALB only` |
| VPC | `dbws-vpc` |
| Inbound | Custom TCP **8000**, Source: security group `dbws-sg-alb` |
| Outbound | All traffic, `0.0.0.0/0` (Engine, endpoint'ler ve NAT üzerinden kod indirme) |

VPC içindeki Engine'ler için modül ayrıca bir **DB security group** (`dbws-sg-db-<engine>`) ister: inbound sadece Engine portu, kaynak `dbws-sg-app-<engine>`.
Böylece Engine'e sadece kendi Engine App'i bağlanabilir.

### E2 - IAM role ve instance profile

**IAM → Roles → Create role**

1. Trusted entity: **AWS service → EC2**.
2. Permissions: `AmazonSSMManagedInstanceCore` (Session Manager için).
3. Role name: `dbws-app-<engine>-eu-central-1` → **Create role**.
4. Rolü açın → **Add permissions → Create inline policy → JSON**: modülün verdiği policy'yi yapıştırın, ad `engine-access`.

Console, EC2 rolü oluştururken aynı adla instance profile'ı da oluşturur.

### E3 - EC2 instance

**EC2 → Instances → Launch instances**

| Alan | Değer |
|---|---|
| Name | `dbws-app-<engine>` (ek etiket: `dbws:engine` = `<engine>`) |
| AMI | Amazon Linux 2023 AMI, **64-bit (Arm)** |
| Instance type | `t4g.medium` |
| Key pair | Proceed without a key pair |
| Network settings → Edit | VPC `dbws-vpc`, Subnet: modül tablosundaki app subnet'i, Auto-assign public IP **Disable** |
| Firewall | Select existing security group: `dbws-sg-app-<engine>` |
| Advanced network configuration → Primary IP | modül tablosundaki sabit IP (ör. `10.20.10.14`) |
| Advanced details → IAM instance profile | `dbws-app-<engine>-eu-central-1` |
| Advanced details → User data | modülün verdiği script |

Alternatif: **Launch instance from template** → `dbws-engine-app` seçip yalnızca yukarıdaki alanları doldurun (disk ve IMDSv2 template'ten gelir).
Şablonu kullanmıyorsanız Advanced details'te **Metadata version: V2 only** seçin ve diski 20 GiB gp3 encrypted yapın.

User data ortak iskeleti (modül kendi `ENGINE`, `URL_PREFIX` ve Engine satırlarını verir):

```bash
#!/bin/bash
set -euxo pipefail
cat > /etc/engine-app.env <<'EOF'
ENGINE=<engine>
URL_PREFIX=/<engine>
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
# ... modülün Engine satırları ...
EOF
dnf install -y git
git clone --depth 1 --branch main https://github.com/sametcntrk/aws-database-workshop.git /opt/engine-app
bash /opt/engine-app/app/deploy/bootstrap.sh
```

`bootstrap.sh` Python 3.11 ortamını kurar, sadece bu Engine'in kütüphanelerini yükler ve `engine-app` systemd servisini başlatır (port 8000).
Kurulum 2-4 dakika sürer. Takip: Session Manager → `sudo tail -f /var/log/cloud-init-output.log`.

### E4 - Target group

**EC2 → Target Groups → Create target group**

| Alan | Değer |
|---|---|
| Target type | Instances |
| Name | `dbws-tg-<engine>` |
| Protocol / Port | HTTP / 8000 |
| VPC | `dbws-vpc` |
| Health check path | `/<engine>/health` |
| Advanced: Healthy threshold / Unhealthy threshold / Interval | 2 / 3 / 15 sn |
| Register targets | `dbws-app-<engine>`, port 8000 → **Include as pending below** |

Oluşturduktan sonra **Attributes → Edit → Deregistration delay** `15` saniye.

### E5 - Listener rule (path based routing)

**EC2 → Load Balancers → dbws-alb → Listeners → HTTPS:443 → Manage rules → Add rule**

| Alan | Değer |
|---|---|
| Name | `<engine>` |
| Condition | **Path** is `/<engine>` **ve** `/<engine>/*` (iki değer) |
| Action | Forward to target group `dbws-tg-<engine>` |
| Priority | modül tablosundaki öncelik |

### E6 - Doğrulama

1. Target group → **Targets**: durum **healthy** olmalı (EC2 açıldıktan 3-5 dk sonra).
2. `https://dbworkshop.tdsynnexlab.link/<engine>/` sayfasını açın.
3. **Seed** (medium) → yazılan kayıtlar ve çalıştırılan işlemler görünür.
4. **Read** → sorgu, süre ve sonuç tablosu görünür.

Sorun giderme:

| Belirti | Kontrol |
|---|---|
| 503 Service Unavailable | Target healthy mi? Listener rule path'i doğru mu? |
| 502 Bad Gateway | Servis çalışıyor mu: Session Manager → `sudo systemctl status engine-app`, `sudo journalctl -u engine-app -n 50` |
| Seed'de zaman aşımı / bağlantı hatası | DB security group inbound kaynağı `dbws-sg-app-<engine>` mi? Engine **Available** mı? |
| `AccessDenied` | IAM inline policy'deki ARN doğru mu? |
| User data hiç çalışmadı | `/var/log/cloud-init-output.log`; NAT gateway ve `dbws-rt-app-*` 0/0 route'u var mı? |
