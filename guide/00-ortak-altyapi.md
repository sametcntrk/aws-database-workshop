# Modül 0 - Ortak altyapı

Bu modül, bütün engine'lerin kullandığı ortak parçaları kurar: ağ, VPC endpoint'leri, ALB, sertifika, DNS kaydı ve yönetici anahtarı.
Modülün sonunda **Engine App deseni** vardır. Her engine modülü bu deseni kendi değerleriyle tekrarlar.

Bütün adımlar **eu-central-1** region'ındadır. Her kaynağa tablodaki adla bir `Name` etiketi verin.

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

VPC'yi oluşturduktan sonra **Actions → Edit VPC settings** ekranını açın.
**Enable DNS resolution** ve **Enable DNS hostnames** seçeneklerinin ikisi de işaretli olmalı.
Interface endpoint'lerin özel DNS adları bu iki ayara ihtiyaç duyar.

## 0.2 Internet gateway

1. **VPC → Internet gateways → Create internet gateway**: Name `dbws-igw`.
2. **Actions → Attach to VPC** ile `dbws-vpc`'ye bağlayın.

## 0.3 Subnet'ler (9 adet)

**VPC → Subnets → Create subnet** ekranında VPC olarak `dbws-vpc`'yi seçin.
Aynı ekranda **Add new subnet** ile dokuz subnet'i birlikte ekleyebilirsiniz.

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

Public subnet'lerde **Auto-assign public IPv4** seçeneğini kapalı bırakın. Public IP'yi yalnızca ALB ve NAT gateway alır.

> **Neden 3 AZ?** Redshift Serverless, Enhanced VPC Routing açıkken 3 farklı AZ'de subnet ister.
> Ağın bütün katmanları bu yüzden aynı 3 AZ'yi kullanır.

## 0.4 NAT gateway'ler (her AZ'de bir tane)

**VPC → NAT gateways → Create NAT gateway** adımını üç kez yapın:

| Name | Subnet | Connectivity type | Elastic IP |
|---|---|---|---|
| `dbws-nat-a` | `dbws-public-a` | Public | **Allocate Elastic IP** |
| `dbws-nat-b` | `dbws-public-b` | Public | **Allocate Elastic IP** |
| `dbws-nat-c` | `dbws-public-c` | Public | **Allocate Elastic IP** |

NAT gateway'lerin durumu 2-3 dakikada **Available** olur. Beklerken bir sonraki adıma geçebilirsiniz.

## 0.5 Route table'lar (her subnet'e bir tane)

**VPC → Route tables → Create route table** ekranında VPC olarak `dbws-vpc`'yi seçin. Her tabloyu oluşturduktan sonra iki iş yapın:
- **Routes → Edit routes**: tablodaki route'u ekleyin.
- **Subnet associations → Edit subnet associations**: tablodaki subnet'i bağlayın.

| Route table | Eklenecek route | Bağlanacak subnet |
|---|---|---|
| `dbws-rt-public-a` | `0.0.0.0/0` → Internet Gateway `dbws-igw` | `dbws-public-a` |
| `dbws-rt-public-b` | `0.0.0.0/0` → Internet Gateway `dbws-igw` | `dbws-public-b` |
| `dbws-rt-public-c` | `0.0.0.0/0` → Internet Gateway `dbws-igw` | `dbws-public-c` |
| `dbws-rt-app-a` | `0.0.0.0/0` → NAT Gateway `dbws-nat-a` | `dbws-app-a` |
| `dbws-rt-app-b` | `0.0.0.0/0` → NAT Gateway `dbws-nat-b` | `dbws-app-b` |
| `dbws-rt-app-c` | `0.0.0.0/0` → NAT Gateway `dbws-nat-c` | `dbws-app-c` |
| `dbws-rt-data-a` | yok (yalnızca `local`) | `dbws-data-a` |
| `dbws-rt-data-b` | yok (yalnızca `local`) | `dbws-data-b` |
| `dbws-rt-data-c` | yok (yalnızca `local`) | `dbws-data-c` |

Her AZ kendi NAT gateway'ini kullanır. Bir AZ arızalanırsa diğer AZ'lerin internet çıkışı etkilenmez.
Data subnet'lerinin internete çıkışı yoktur.

## 0.6 Gateway endpoint'ler (S3 ve DynamoDB)

**VPC → Endpoints → Create endpoint** adımını iki kez yapın:

| Alan | S3 | DynamoDB |
|---|---|---|
| Name | `dbws-vpce-s3` | `dbws-vpce-dynamodb` |
| Type | AWS services | AWS services |
| Service | `com.amazonaws.eu-central-1.s3`, Type **Gateway** | `com.amazonaws.eu-central-1.dynamodb`, Type **Gateway** |
| VPC | `dbws-vpc` | `dbws-vpc` |
| Route tables | `dbws-rt-app-a`, `dbws-rt-app-b`, `dbws-rt-app-c` | aynı üç tablo |
| Policy | Full access | Full access |

Sonuçta app route table'larına iki satır eklenir: `pl-xxxx (S3)` ve `pl-xxxx (DynamoDB)`, ikisi de `vpce-...` hedefine gider.
Bu iki servise giden trafik artık NAT gateway'e uğramaz.

## 0.7 Interface endpoint'ler

Önce endpoint'lerin security group'unu oluşturun: **EC2 → Security Groups → Create security group**

| Alan | Değer |
|---|---|
| Name | `dbws-sg-vpce` |
| Description | `Interface endpoints - HTTPS and Keyspaces (9142) from the app subnets` |
| VPC | `dbws-vpc` |
| Inbound | TCP 443 kaynak `10.20.10.0/24`, `10.20.11.0/24`, `10.20.12.0/24`. TCP 9142 kaynak aynı üç CIDR. |
| Outbound | varsayılan (All traffic) |

Sonra **VPC → Endpoints → Create endpoint** adımını beş kez yapın. Type: AWS services, Type: **Interface**.

| Name | Service |
|---|---|
| `dbws-vpce-secretsmanager` | `com.amazonaws.eu-central-1.secretsmanager` |
| `dbws-vpce-keyspaces` | `com.amazonaws.eu-central-1.cassandra` |
| `dbws-vpce-ssm` | `com.amazonaws.eu-central-1.ssm` |
| `dbws-vpce-ssmmessages` | `com.amazonaws.eu-central-1.ssmmessages` |
| `dbws-vpce-ec2messages` | `com.amazonaws.eu-central-1.ec2messages` |

Her endpoint için şu değerleri kullanın:
- VPC: `dbws-vpc`
- **Enable DNS name**: işaretli
- Subnets: **data** subnet'leri, yani `dbws-data-a`, `dbws-data-b`, `dbws-data-c` (her AZ'de bir tane)
- Security groups: `dbws-sg-vpce`
- Policy: Full access

> Endpoint ENI'leri data subnet'lerinde, kullanan engine'lerin yanında durur.
> Bir Engine App `secretsmanager.eu-central-1.amazonaws.com` adını sorduğunda, kendi AZ'sindeki ENI'nin private IP'sini alır.

## 0.8 Yönetici anahtarı (Admin Console)

Sitenin **Admin Console** sayfası, veriyi yükleyen ve sıfırlayan sayfadır. Bu sayfa bir anahtar ister.
Anahtarı CloudShell ile üretin ve Secrets Manager'a kaydedin:

```bash
KEY=$(aws secretsmanager get-random-password --password-length 24 --exclude-punctuation --query RandomPassword --output text)
aws secretsmanager create-secret --region eu-central-1 --name dbws/admin \
  --description "Admin Console key of the Lale Market Storefront (instructor only)" \
  --secret-string "{\"key\":\"$KEY\"}"
```

Çıktıdaki **ARN** değerini not alın. Her Engine App bu secret'ı okur.

## 0.9 ALB security group

**EC2 → Security Groups → Create security group**

| Alan | Değer |
|---|---|
| Name | `dbws-sg-alb` |
| Description | `ALB - HTTPS 443 and HTTP 80 (redirect) from AllowedCidr` |
| VPC | `dbws-vpc` |
| Inbound | TCP 443 kaynak `0.0.0.0/0`. TCP 80 kaynak `0.0.0.0/0`. Workshop salonunun IP'sini biliyorsanız `x.x.x.x/32` yazın. |

## 0.10 Sertifika (ACM)

**Certificate Manager (eu-central-1) → Request → Request a public certificate**

| Alan | Değer |
|---|---|
| Fully qualified domain name | `dbworkshop.tdsynnexlab.link` |
| Validation method | DNS validation |
| Key algorithm | RSA 2048 |

Sertifikayı açın ve **Create records in Route 53 → Create records** seçin. Durum 2-5 dakikada **Issued** olur.

## 0.11 Application Load Balancer

**EC2 → Load Balancers → Create load balancer → Application Load Balancer**

| Alan | Değer |
|---|---|
| Name | `dbws-alb` |
| Scheme | Internet-facing |
| IP address type | IPv4 |
| VPC | `dbws-vpc` |
| Mappings | eu-central-1a `dbws-public-a`, eu-central-1b `dbws-public-b`, eu-central-1c `dbws-public-c` |
| Security groups | yalnızca `dbws-sg-alb` |

**Listener 1 - HTTPS : 443**

| Alan | Değer |
|---|---|
| Default action | Şimdilik **Return fixed response**: 503, Content type `text/plain`, body `Lale Market opens soon.` Modül 8'de bu ayarı DocumentDB App'e yönlendireceksiniz. |
| Security policy | `ELBSecurityPolicy-TLS13-1-2-2021-06` |
| Default SSL/TLS certificate | From ACM: `dbworkshop.tdsynnexlab.link` |

**Listener 2 - HTTP : 80**: Default action **Redirect to URL**, Protocol HTTPS, Port 443, Status code 301.

ALB oluştuktan sonra **Attributes → Edit** ekranında iki ayarı değiştirin:
- **Drop invalid header fields**: açık
- **Connection idle timeout**: `120` saniye. Büyük veri yükleme işlemleri 60 saniyeyi geçebilir.

## 0.12 DNS kaydı

**Route 53 → Hosted zones → tdsynnexlab.link → Create record**

| Alan | Değer |
|---|---|
| Record name | `dbworkshop` |
| Record type | A |
| Alias | açık → Alias to Application and Classic Load Balancer → Europe (Frankfurt) → `dbws-alb` |
| Evaluate target health | No |

Doğrulama: tarayıcıda `https://dbworkshop.tdsynnexlab.link/` adresi "Lale Market opens soon." yazısını göstermeli.

## 0.13 Launch template (bütün Engine App'ler için)

**EC2 → Launch Templates → Create launch template**

| Alan | Değer |
|---|---|
| Name | `dbws-engine-app` |
| AMI, instance type, key pair, network | boş bırakın. Bunlar instance oluştururken seçilir. |
| Storage | Volume 1 (`/dev/xvda`): 20 GiB, **gp3**, Encrypted **Yes**, Delete on termination **Yes** |
| Advanced details → Metadata version | **V2 only (token required)** |
| Advanced details → Metadata response hop limit | `1` |
| Advanced details → Detailed CloudWatch monitoring | Enable |

EC2'lere SSH anahtarı ve public IP verilmez. Bir instance'a bağlanmak için **Systems Manager → Session Manager** kullanılır.
Bunu 0.7'deki SSM endpoint'leri sağlar.

---

## Engine App deseni (her engine modülünde tekrarlanır)

Her engine modülü önce kendi engine'ini kurar. Sonra aşağıdaki altı adımı **o modülün tablosundaki değerlerle** yapar.
Metindeki `<engine>` yerine modülün kimliğini yazın: `aurora`, `redshift`, `dynamodb`, `elasticache`, `keyspaces`, `influxdb`, `neptune`, `docdb`, `s3` veya `opensearch`.

### E1 - App security group

**EC2 → Security Groups → Create security group**

| Alan | Değer |
|---|---|
| Name | `dbws-sg-app-<engine>` |
| Description | `Engine App <Engine> - HTTP 8000 from the ALB only` |
| VPC | `dbws-vpc` |
| Inbound | Custom TCP **8000**, kaynak: security group `dbws-sg-alb` |
| Outbound | All traffic, `0.0.0.0/0`. Engine'e, endpoint'lere ve kod indirmek için NAT'a çıkış gerekir. |

VPC içindeki engine'ler için modül ayrıca bir **DB security group** ister: `dbws-sg-db-<engine>`.
Bu grubun inbound kuralı yalnızca engine'in portunu açar ve kaynak olarak yalnızca `dbws-sg-app-<engine>`'i kabul eder.
Böylece engine'e yalnızca kendi Engine App'i bağlanabilir.

### E2 - IAM role ve instance profile

**IAM → Roles → Create role**

1. Trusted entity: **AWS service → EC2**.
2. Permissions: `AmazonSSMManagedInstanceCore`. Bu policy Session Manager bağlantısını sağlar.
3. Role name: `dbws-app-<engine>-eu-central-1` → **Create role**.
4. Rolü açın → **Add permissions → Create inline policy → JSON**. Modülün verdiği policy'yi yapıştırın. Policy adı: `engine-access`.

Her modülün policy'si, yönetici anahtarını okuma iznini de içerir:

```json
{ "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": "<dbws/admin secret ARN>" }
```

Console, EC2 için rol oluştururken aynı adla bir instance profile da oluşturur.

### E3 - EC2 instance

**EC2 → Instances → Launch instances**

| Alan | Değer |
|---|---|
| Name | `dbws-app-<engine>`. Ek etiket: `dbws:engine` = `<engine>` |
| AMI | Amazon Linux 2023 AMI, **64-bit (Arm)** |
| Instance type | `t4g.medium` |
| Key pair | Proceed without a key pair |
| Network settings → Edit | VPC `dbws-vpc`, Subnet: modül tablosundaki app subnet'i, Auto-assign public IP **Disable** |
| Firewall | Select existing security group: `dbws-sg-app-<engine>` |
| Advanced network configuration → Primary IP | modül tablosundaki sabit IP, örneğin `10.20.10.14` |
| Advanced details → IAM instance profile | `dbws-app-<engine>-eu-central-1` |
| Advanced details → User data | modülün verdiği script |

Kolay yol: **Launch instance from template** ekranında `dbws-engine-app` şablonunu seçin ve yalnızca yukarıdaki alanları doldurun.
Disk ve IMDSv2 ayarları şablondan gelir. Şablonu kullanmazsanız Advanced details'te **Metadata version: V2 only** seçin
ve diski 20 GiB gp3 encrypted yapın.

User data'nın ortak iskeleti aşağıdadır. Modül, kendi `ENGINE` değerini ve engine'e özel satırları verir:

```bash
#!/bin/bash
set -euxo pipefail
cat > /etc/engine-app.env <<'EOF'
ENGINE=<engine>
URL_PREFIX=/<engine>
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
ADMIN_SECRET_ARN=<dbws/admin secret ARN>
# ... modülün engine satırları ...
EOF
dnf install -y git
git clone --depth 1 --branch main https://github.com/sametcntrk/aws-database-workshop.git /opt/engine-app
bash /opt/engine-app/app/deploy/bootstrap.sh
```

`bootstrap.sh` şunları yapar: Python 3.11 ortamını kurar, yalnızca bu engine'in kütüphanelerini yükler ve `engine-app`
servisini 8000 portunda başlatır. Kurulum 2-4 dakika sürer.
Kurulumu izlemek için Session Manager ile bağlanın ve `sudo tail -f /var/log/cloud-init-output.log` komutunu çalıştırın.

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

Oluşturduktan sonra **Attributes → Edit → Deregistration delay** değerini `15` saniye yapın.

### E5 - Listener rule (yola göre yönlendirme)

**EC2 → Load Balancers → dbws-alb → Listeners → HTTPS:443 → Manage rules → Add rule**

| Alan | Değer |
|---|---|
| Name | `<engine>` |
| Condition | **Path**: modül tablosundaki yolların hepsi, örneğin `/checkout`, `/orders`, `/admin/orders`, `/aurora/*` |
| Action | Forward to target group `dbws-tg-<engine>` |
| Priority | modül tablosundaki öncelik |

Bir kural en fazla 5 yol değeri alır. Bu rehberdeki hiçbir kural bu sınırı aşmaz.

### E6 - Doğrulama

1. Target group'un **Targets** sekmesinde durum **healthy** olmalı. Bu, EC2 açıldıktan 3-5 dakika sonra olur.
2. Modülün **Doğrulama** bölümündeki sayfayı açın.
3. Sayfa boşsa, Admin Console'dan bu engine için **Seed** yapın. Bkz. Modül 8, adım 8.5.
4. Sayfayı kullanın ve sağdaki **Behind the scenes** panelinde engine çağrılarını görün.

Sorun giderme:

| Belirti | Kontrol edilecek yer |
|---|---|
| 503 Service Unavailable | Target healthy mi? Listener rule'daki yollar doğru mu? |
| 502 Bad Gateway | Servis çalışıyor mu? Session Manager ile bağlanın: `sudo systemctl status engine-app` ve `sudo journalctl -u engine-app -n 50` |
| Panelde zaman aşımı veya bağlantı hatası | DB security group'un inbound kaynağı `dbws-sg-app-<engine>` mi? Engine **Available** durumunda mı? |
| `AccessDenied` | IAM inline policy'deki ARN'ler doğru mu? `dbws/admin` izni var mı? |
| User data hiç çalışmadı | `/var/log/cloud-init-output.log` dosyasına bakın. NAT gateway ve `dbws-rt-app-*` tablosundaki 0/0 route'u var mı? |
