# Temizlik

Kaynaklar silinmezse saatlik ücretlendirme devam eder. En pahalıları: OpenSearch, DocumentDB, Neptune, NAT gateway'ler ve InfluxDB.

## Eğitmen (CloudFormation)

```bash
aws cloudformation delete-stack --region eu-central-1 --stack-name dbws-workshop
```

S3 bucket'ını stack içindeki küçük bir Lambda fonksiyonu boşaltır. Ayrıca bir şey yapmanız gerekmez. Silme 20-30 dakika sürer.

## Katılımcı (Console)

Kaynakları bu sırayla silin. Bir kaynak silinmezse, ona bağlı başka bir kaynak hâlâ duruyordur.

1. **Zero-ETL integration:** RDS → Zero-ETL integrations → `dbws-aurora-to-redshift` → Delete.
2. **Listener rule'lar ve target group'lar:** `dbws-alb` → HTTPS:443 → kuralları silin. Sonra `dbws-tg-*` target group'larını silin.
3. **EC2 instance'lar:** `dbws-app-*` → Terminate.
4. **Engine'ler.** Bunları aynı anda silebilirsiniz:
   - OpenSearch domain `dbws-search`
   - DocumentDB: önce iki instance, sonra cluster `dbws-docdb` (final snapshot almayın)
   - Neptune: önce reader, sonra writer, sonra cluster `dbws-neptune`
   - Aurora: önce reader, sonra writer, sonra cluster `dbws-aurora` (final snapshot almayın). Sonra parametre grubu `dbws-aurora-zeroetl`.
   - Timestream InfluxDB `dbws-influxdb`
   - ElastiCache: önce cache `dbws-cache`, sonra user group `dbws-users`, sonra user `dbws-app`
   - Redshift Serverless: önce workgroup `dbws`, sonra namespace `dbws`
   - Keyspaces keyspace `dbws`
   - DynamoDB tablo `dbws-cart`
   - S3: bucket'ı **Empty** ile bütün sürümleriyle boşaltın, sonra **Delete**
5. **Subnet group'lar:** RDS `dbws-aurora`, Neptune `dbws-neptune`, DocumentDB `dbws-docdb`.
6. **Secrets Manager:** `dbws/admin`, `dbws/redshift`, `dbws/elasticache`, `dbws/influxdb`, `dbws/docdb` → Delete.
   Konsoldaki en kısa bekleme süresi 7 gündür. Hemen silmek için CLI'da `--force-delete-without-recovery` kullanın.
   Aurora'nın `rds!cluster-...` secret'ı cluster ile birlikte silinir.
7. **ALB** `dbws-alb`, **Route 53** kaydı `dbworkshop`, **ACM** sertifikası.
8. **VPC endpoint'leri** (7 adet) ve **NAT gateway'ler** (3 adet). Sonra **Elastic IP'leri** Release edin.
9. **Security group'lar** `dbws-sg-*`. Birbirine referans veren kuralları önce silmeniz gerekebilir.
10. **VPC** `dbws-vpc` → Delete VPC. Bu adım subnet'leri, route table'ları ve internet gateway'i de siler.
11. **IAM:** `dbws-app-*-eu-central-1` rolleri ve instance profile'ları. Launch template `dbws-engine-app`.
