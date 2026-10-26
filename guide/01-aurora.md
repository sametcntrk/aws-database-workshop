# Modül 1 - Aurora PostgreSQL Serverless v2 (Structured · Relational)

**Domain dilimi:** müşteriler ve siparişler. **Read:** `JOIN orders ↔ customers`, gelire göre ilk 10 müşteri.
**Bağlantı:** PostgreSQL wire protokolü, TCP 5432, TLS, kullanıcı adı/şifre (RDS'in yönettiği Secrets Manager secret'ı).

## 1.1 DB security group

**EC2 → Security Groups → Create security group**: Name `dbws-sg-db-aurora`, Description `Aurora engine - reachable only from the Aurora Engine App`, VPC `dbws-vpc`.
Inbound: **PostgreSQL TCP 5432**, Source `dbws-sg-app-aurora`.

`dbws-sg-app-aurora` henüz yoksa önce Modül 0 → **E1**'i yapın (Name `dbws-sg-app-aurora`).

## 1.2 DB subnet group

**RDS → Subnet groups → Create DB subnet group**: Name `dbws-aurora`, Description `Aurora - data subnets`, VPC `dbws-vpc`,
AZ'ler a/b/c, Subnets `10.20.20.0/24`, `10.20.21.0/24`, `10.20.22.0/24`.

## 1.3 Aurora cluster

**RDS → Databases → Create database → Full configuration**

| Alan | Değer |
|---|---|
| Engine | Aurora (PostgreSQL Compatible), version **17.9** |
| Templates | Dev/Test |
| DB cluster identifier | `dbws-aurora` |
| Master username | `dbwsadmin` |
| Credentials management | **Managed in AWS Secrets Manager** (KMS key: aws/secretsmanager) |
| Cluster storage configuration | Aurora Standard |
| Instance configuration | **Serverless v2**, Min **0.5 ACU**, Max **4 ACU** |
| Availability & durability | **Create an Aurora Replica in a different AZ** |
| VPC | `dbws-vpc`, DB subnet group `dbws-aurora` |
| Public access | No |
| VPC security group | Choose existing: sadece `dbws-sg-db-aurora` (default'u kaldırın) |
| Availability Zone | eu-central-1a (writer) |
| Additional configuration → Initial database name | `shop` |
| Backup retention | 1 day |
| Encryption | Enable encryption (aws/rds) |
| Deletion protection | kapalı |

Oluşan instance adlarını `dbws-aurora-writer` (AZ a) ve `dbws-aurora-reader` (AZ b) olarak değiştirebilirsiniz (isteğe bağlı).
Oluşturma 10-15 dk sürer. Beklerken 1.4'e geçin.

Not alın:
- **Writer endpoint:** `dbws-aurora.cluster-xxxx.eu-central-1.rds.amazonaws.com` (Connectivity & security sekmesi)
- **Secret ARN:** Configuration sekmesi → Master credentials ARN (`arn:aws:secretsmanager:eu-central-1:<ACCOUNT_ID>:secret:rds!cluster-...`)

## 1.4 Engine App (Modül 0 → Engine App deseni)

| Adım | Değer |
|---|---|
| E1 | `dbws-sg-app-aurora` |
| E2 role | `dbws-app-aurora-eu-central-1` |
| E3 | Subnet `dbws-app-a`, IP `10.20.10.14` |
| E4 | `dbws-tg-aurora`, health check `/aurora/health` |
| E5 | Path `/aurora`, `/aurora/*`, öncelik **10** |

E2 inline policy (`engine-access`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "secretsmanager:GetSecretValue",
      "Resource": "<Aurora master credentials secret ARN>" }
  ]
}
```

E3 user data, Engine satırları:

```bash
ENGINE=aurora
URL_PREFIX=/aurora
AWS_REGION=eu-central-1
AWS_DEFAULT_REGION=eu-central-1
DB_HOST=<writer endpoint>
DB_PORT=5432
DB_NAME=shop
DB_SECRET_ARN=<Aurora master credentials secret ARN>
```

## 1.5 Doğrulama

`https://dbworkshop.tdsynnexlab.link/aurora/` → **Seed** (DDL + 4 tablo COPY, tek transaction) → **Read** (2 JOIN'li rapor).

Deneyin: Seed'i `large` ile çalıştırın; Monitoring sekmesinde ACU'nun 0.5'ten yükseldiğini görün.
