# Temizlik

Kaynaklar silinmezse saatlik ücret sürer (en pahalıları: OpenSearch, DocumentDB, Neptune, NAT gateway'ler, InfluxDB).

## Eğitmen (CloudFormation)

```bash
aws cloudformation delete-stack --region eu-central-1 --stack-name dbws-workshop
```

S3 bucket'ı stack içindeki küçük bir Lambda boşaltır, ayrıca bir şey yapmanız gerekmez. Silme 20-30 dk sürer.

## Katılımcı (Console) - bu sırayla

1. **Listener rule'lar ve target group'lar**: `dbws-alb` → HTTPS:443 → kuralları silin; sonra `dbws-tg-*`.
2. **EC2 instance'lar**: `dbws-app-*` → Terminate.
3. **Engine'ler** (paralel silebilirsiniz):
   - OpenSearch domain `dbws-search`
   - DocumentDB: önce iki instance, sonra cluster `dbws-docdb` (final snapshot almayın)
   - Neptune: önce reader, sonra writer, sonra cluster `dbws-neptune`
   - Aurora: önce reader, sonra writer, sonra cluster `dbws-aurora` (final snapshot almayın)
   - Timestream InfluxDB `dbws-influxdb`
   - ElastiCache cache `dbws-cache`, sonra user group `dbws-users`, sonra user `dbws-app`
   - Redshift Serverless workgroup `dbws`, sonra namespace `dbws`
   - Keyspaces keyspace `dbws`
   - DynamoDB tablo `dbws-cart`
   - S3: bucket'ı **Empty** (bütün sürümler dahil), sonra **Delete**
4. **Subnet group'lar**: RDS `dbws-aurora`, Neptune `dbws-neptune`, DocumentDB `dbws-docdb`.
5. **Secrets Manager**: `dbws/redshift`, `dbws/elasticache`, `dbws/influxdb`, `dbws/docdb` → Delete (en kısa bekleme 7 gün; hemen silmek için CLI `--force-delete-without-recovery`). Aurora'nın `rds!cluster-...` secret'ı cluster ile birlikte silinir.
6. **ALB** `dbws-alb`, **Route 53** kaydı `dbworkshop`, **ACM** sertifikası.
7. **VPC endpoint'leri** (7 adet), **NAT gateway'ler** (3 adet), sonra **Elastic IP'leri** Release edin.
8. **Security group'lar** `dbws-sg-*` (önce birbirine referans veren kuralları silmeniz gerekebilir).
9. **VPC** `dbws-vpc` → Delete VPC (subnet'leri, route table'ları ve internet gateway'i birlikte siler).
10. **IAM**: `dbws-app-*-eu-central-1` rolleri ve instance profile'ları; launch template `dbws-engine-app`.
