#!/usr/bin/env python3
"""Generate cloudformation/workshop.yaml.

The ten Engine Apps share the same pattern (security group, IAM role, target group, listener rule,
EC2 instance), so this script writes those blocks from one table. Everything else is plain YAML.
Usage: python3 gen_template.py ../workshop.yaml
"""
import sys
import textwrap

OUT = sys.argv[1]

# engine id, label, AZ index, ALB priority, engine port(s) for its DB security group (None = no VPC engine)
APPS = [
    ("aurora", "Aurora", 0, 10, [5432]),
    ("redshift", "Redshift", 2, 20, [5439]),
    ("dynamodb", "DynamoDB", 0, 30, None),
    ("elasticache", "ElastiCache", 1, 40, [6379, 6380]),
    ("keyspaces", "Keyspaces", 0, 50, None),
    ("influxdb", "InfluxDB", 2, 60, [8086]),
    ("neptune", "Neptune", 1, 70, [8182]),
    ("docdb", "DocumentDB", 1, 80, [27017]),
    ("s3", "S3", 0, 90, None),
    ("opensearch", "OpenSearch", 2, 100, [443]),
]
AZ = ["A", "B", "C"]
# fixed Engine App IPs (same as the architecture diagram)
IPS = {"dynamodb": "10.20.10.11", "s3": "10.20.10.12", "keyspaces": "10.20.10.13", "aurora": "10.20.10.14",
       "neptune": "10.20.11.11", "docdb": "10.20.11.12", "elasticache": "10.20.11.13",
       "opensearch": "10.20.12.11", "redshift": "10.20.12.12", "influxdb": "10.20.12.13"}


def cap(e):
    return {"aurora": "Aurora", "redshift": "Redshift", "dynamodb": "DynamoDb", "elasticache": "ElastiCache",
            "keyspaces": "Keyspaces", "influxdb": "InfluxDb", "neptune": "Neptune", "docdb": "DocDb",
            "s3": "S3", "opensearch": "OpenSearch"}[e]


# Engine-specific environment lines for /etc/engine-app.env (inside Fn::Sub)
ENV = {
    "aurora": ["DB_HOST=${AuroraCluster.Endpoint.Address}", "DB_PORT=5432", "DB_NAME=shop",
               "DB_SECRET_ARN=${AuroraCluster.MasterUserSecret.SecretArn}"],
    "redshift": ["DB_HOST=${RedshiftWorkgroup.Workgroup.Endpoint.Address}", "DB_PORT=5439", "DB_NAME=dev",
                 "DB_SECRET_ARN=${RedshiftSecret}"],
    "dynamodb": ["TABLE_NAME=${CartTable}"],
    "elasticache": ["CACHE_HOST=${Cache.Endpoint.Address}", "CACHE_PORT=${Cache.Endpoint.Port}",
                    "CACHE_SECRET_ARN=${CacheUserSecret}"],
    "keyspaces": ["KEYSPACE=${ActivityKeyspace}", "TABLE_NAME=activity_by_user"],
    "influxdb": ["INFLUX_URL=https://${InfluxDb.Endpoint}:8086", "INFLUX_ORG=dbws", "INFLUX_BUCKET=metrics",
                 "INFLUX_SECRET_ARN=${InfluxDbSecret}"],
    "neptune": ["NEPTUNE_HOST=${NeptuneCluster.Endpoint}", "NEPTUNE_PORT=${NeptuneCluster.Port}"],
    "docdb": ["DB_HOST=${DocDbCluster.Endpoint}", "DB_PORT=27017", "DB_SECRET_ARN=${DocDbSecret}"],
    "s3": ["BUCKET_NAME=${ImageBucket}"],
    "opensearch": ["OS_HOST=${SearchDomain.DomainEndpoint}"],
}

# Engine-specific IAM statements (YAML, indented later)
POLICY = {
    "aurora": """\
- Effect: Allow
  Action: secretsmanager:GetSecretValue
  Resource: !GetAtt AuroraCluster.MasterUserSecret.SecretArn""",
    "redshift": """\
- Effect: Allow
  Action: secretsmanager:GetSecretValue
  Resource: !Ref RedshiftSecret""",
    "dynamodb": """\
- Effect: Allow
  Action:
    - dynamodb:DescribeTable
    - dynamodb:Query
    - dynamodb:Scan
    - dynamodb:GetItem
    - dynamodb:PutItem
    - dynamodb:DeleteItem
    - dynamodb:BatchWriteItem
  Resource: !GetAtt CartTable.Arn""",
    "elasticache": """\
- Effect: Allow
  Action: secretsmanager:GetSecretValue
  Resource: !Ref CacheUserSecret""",
    "keyspaces": """\
- Effect: Allow
  Action:
    - cassandra:Select
    - cassandra:Modify
  Resource:
    - !Sub arn:${AWS::Partition}:cassandra:${AWS::Region}:${AWS::AccountId}:/keyspace/${ActivityKeyspace}/
    - !Sub arn:${AWS::Partition}:cassandra:${AWS::Region}:${AWS::AccountId}:/keyspace/${ActivityKeyspace}/table/activity_by_user
- Effect: Allow
  Action: cassandra:Select
  Resource: !Sub arn:${AWS::Partition}:cassandra:${AWS::Region}:${AWS::AccountId}:/keyspace/system*
- Effect: Allow
  Action:
    - ec2:DescribeNetworkInterfaces
    - ec2:DescribeVpcEndpoints
  Resource: '*'""",
    "influxdb": """\
- Effect: Allow
  Action: secretsmanager:GetSecretValue
  Resource: !Ref InfluxDbSecret""",
    "neptune": """\
- Effect: Allow
  Action:
    - neptune-db:connect
    - neptune-db:ReadDataViaQuery
    - neptune-db:WriteDataViaQuery
    - neptune-db:DeleteDataViaQuery
  Resource: !Sub arn:${AWS::Partition}:neptune-db:${AWS::Region}:${AWS::AccountId}:${NeptuneCluster.ClusterResourceId}/*""",
    "docdb": """\
- Effect: Allow
  Action: secretsmanager:GetSecretValue
  Resource: !Ref DocDbSecret""",
    "s3": """\
- Effect: Allow
  Action: s3:ListBucket
  Resource: !GetAtt ImageBucket.Arn
- Effect: Allow
  Action:
    - s3:GetObject
    - s3:PutObject
    - s3:DeleteObject
  Resource: !Sub ${ImageBucket.Arn}/*""",
    "opensearch": """\
- Effect: Allow
  Action:
    - es:ESHttpGet
    - es:ESHttpHead
    - es:ESHttpPost
    - es:ESHttpPut
    - es:ESHttpDelete
  Resource: !Sub arn:${AWS::Partition}:es:${AWS::Region}:${AWS::AccountId}:domain/dbws-search/*""",
}


def ind(text, n):
    return textwrap.indent(text, " " * n)


def app_blocks():
    out = []
    for eid, label, azi, prio, ports in APPS:
        C = cap(eid)
        out.append(f"""
  # ---------------------------------------------------------------- Engine App: {label}
  AppSg{C}:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: dbws-sg-app-{eid}
      GroupDescription: Engine App {label} - HTTP 8000 from the ALB only
      VpcId: !Ref Vpc
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8000
          ToPort: 8000
          SourceSecurityGroupId: !Ref AlbSg
          Description: ALB to Engine App
      SecurityGroupEgress:
        - IpProtocol: '-1'
          CidrIp: 0.0.0.0/0
          Description: Engine, VPC endpoints and NAT (code download)
      Tags:
        - Key: Name
          Value: dbws-sg-app-{eid}
""")
        if ports:
            ingress = "".join(f"""
        - IpProtocol: tcp
          FromPort: {p}
          ToPort: {p}
          SourceSecurityGroupId: !Ref AppSg{C}
          Description: Engine App {label} only""" for p in ports)
            out.append(f"""
  DbSg{C}:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: dbws-sg-db-{eid}
      GroupDescription: {label} engine - reachable only from the {label} Engine App
      VpcId: !Ref Vpc
      SecurityGroupIngress:{ingress}
      Tags:
        - Key: Name
          Value: dbws-sg-db-{eid}
""")
        out.append(f"""
  AppRole{C}:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub dbws-app-{eid}-${{AWS::Region}}
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - !Sub arn:${{AWS::Partition}}:iam::aws:policy/AmazonSSMManagedInstanceCore
      Policies:
        - PolicyName: engine-access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
{ind(POLICY[eid], 14)}

  AppProfile{C}:
    Type: AWS::IAM::InstanceProfile
    Properties:
      InstanceProfileName: !Sub dbws-app-{eid}-${{AWS::Region}}
      Roles:
        - !Ref AppRole{C}

  Tg{C}:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: dbws-tg-{eid}
      VpcId: !Ref Vpc
      Protocol: HTTP
      Port: 8000
      TargetType: instance
      HealthCheckPath: /{eid}/health
      HealthCheckIntervalSeconds: 15
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3
      TargetGroupAttributes:
        - Key: deregistration_delay.timeout_seconds
          Value: '15'
      Targets:
        - Id: !Ref App{C}
          Port: 8000

  Rule{C}:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      ListenerArn: !Ref HttpsListener
      Priority: {prio}
      Conditions:
        - Field: path-pattern
          PathPatternConfig:
            Values:
              - /{eid}
              - /{eid}/*
      Actions:
        - Type: forward
          TargetGroupArn: !Ref Tg{C}

  App{C}:
    Type: AWS::EC2::Instance
    DependsOn: [NatRoute{AZ[azi]}, VpcEndpointSecretsManager, VpcEndpointSsm]
    Properties:
      LaunchTemplate:
        LaunchTemplateId: !Ref AppLaunchTemplate
        Version: !GetAtt AppLaunchTemplate.LatestVersionNumber
      ImageId: !Ref LatestAmiId
      InstanceType: !Ref InstanceType
      SubnetId: !Ref AppSubnet{AZ[azi]}
      PrivateIpAddress: {IPS[eid]}
      SecurityGroupIds:
        - !Ref AppSg{C}
      IamInstanceProfile: !Ref AppProfile{C}
      Tags:
        - Key: Name
          Value: dbws-app-{eid}
        - Key: dbws:engine
          Value: {eid}
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash
          set -euxo pipefail
          cat > /etc/engine-app.env <<'EOF'
          ENGINE={eid}
          URL_PREFIX=/{eid}
          AWS_REGION=${{AWS::Region}}
          AWS_DEFAULT_REGION=${{AWS::Region}}
{ind(chr(10).join(ENV[eid]), 10)}
          EOF
          dnf install -y git
          git clone --depth 1 --branch ${{AppRepoRef}} ${{AppRepoUrl}} /opt/engine-app
          bash /opt/engine-app/app/deploy/bootstrap.sh
""")
    return "".join(out)


HEADER = r"""AWSTemplateFormatVersion: '2010-09-09'
Description: >-
  AWS Database Workshop (dbws) - ten Engine Apps behind one HTTPS ALB. Each EC2 Engine App seeds e-commerce
  data into its own Engine (Aurora PostgreSQL, Redshift Serverless, DynamoDB, ElastiCache Serverless,
  Keyspaces, Timestream for InfluxDB, Neptune, DocumentDB, S3, OpenSearch), reads it back and shows it on a web page.
  Region: eu-central-1 (needs 3 AZs). Generated by cloudformation/src/gen_template.py.

Metadata:
  AWS::CloudFormation::Interface:
    ParameterGroups:
      - Label: {default: Web access}
        Parameters: [DomainName, HostedZoneId, AllowedCidr]
      - Label: {default: Engine Apps}
        Parameters: [AppRepoUrl, AppRepoRef, InstanceType, LatestAmiId]
      - Label: {default: Account prerequisites}
        Parameters: [CreateOpenSearchServiceLinkedRole]

Parameters:
  DomainName:
    Type: String
    Default: dbworkshop.tdsynnexlab.link
    Description: Host name for the ALB. Must be inside the hosted zone below.
  HostedZoneId:
    Type: AWS::Route53::HostedZone::Id
    Description: Public Route 53 hosted zone that contains DomainName (for the alias record and ACM DNS validation).
  AllowedCidr:
    Type: String
    Default: 0.0.0.0/0
    AllowedPattern: ^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$
    Description: Who may open the web apps (for example the workshop room public IP /32).
  AppRepoUrl:
    Type: String
    Default: https://github.com/sametcntrk/aws-database-workshop.git
    Description: Public Git repository with the Engine App code.
  AppRepoRef:
    Type: String
    Default: main
    Description: Branch or tag to deploy.
  InstanceType:
    Type: String
    Default: t4g.medium
    AllowedValues: [t4g.small, t4g.medium, t4g.large, m7g.medium, m7g.large]
    Description: Engine App instance type (arm64).
  LatestAmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64
  CreateOpenSearchServiceLinkedRole:
    Type: String
    Default: 'true'
    AllowedValues: ['true', 'false']
    Description: Set to false if the account already has AWSServiceRoleForAmazonOpenSearchService.

Conditions:
  CreateOsSlr: !Equals [!Ref CreateOpenSearchServiceLinkedRole, 'true']

Resources:
  # ================================================================ Network (Module 0)
  Vpc:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.20.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: dbws-vpc

  Igw:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: dbws-igw

  IgwAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref Vpc
      InternetGatewayId: !Ref Igw
"""


def network():
    out = []
    for i, z in enumerate(AZ):
        az = z.lower()
        out.append(f"""
  PublicSubnet{z}:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref Vpc
      CidrBlock: 10.20.{i}.0/24
      AvailabilityZone: !Sub ${{AWS::Region}}{az}
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: dbws-public-{az}

  AppSubnet{z}:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref Vpc
      CidrBlock: 10.20.{10 + i}.0/24
      AvailabilityZone: !Sub ${{AWS::Region}}{az}
      Tags:
        - Key: Name
          Value: dbws-app-{az}

  DataSubnet{z}:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref Vpc
      CidrBlock: 10.20.{20 + i}.0/24
      AvailabilityZone: !Sub ${{AWS::Region}}{az}
      Tags:
        - Key: Name
          Value: dbws-data-{az}

  NatEip{z}:
    Type: AWS::EC2::EIP
    DependsOn: IgwAttachment
    Properties:
      Domain: vpc
      Tags:
        - Key: Name
          Value: dbws-nat-eip-{az}

  NatGw{z}:
    Type: AWS::EC2::NatGateway
    Properties:
      SubnetId: !Ref PublicSubnet{z}
      AllocationId: !GetAtt NatEip{z}.AllocationId
      Tags:
        - Key: Name
          Value: dbws-nat-{az}

  PublicRt{z}:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc
      Tags:
        - Key: Name
          Value: dbws-rt-public-{az}

  PublicRoute{z}:
    Type: AWS::EC2::Route
    DependsOn: IgwAttachment
    Properties:
      RouteTableId: !Ref PublicRt{z}
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref Igw

  PublicRtAssoc{z}:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet{z}
      RouteTableId: !Ref PublicRt{z}

  AppRt{z}:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc
      Tags:
        - Key: Name
          Value: dbws-rt-app-{az}

  NatRoute{z}:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref AppRt{z}
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGw{z}

  AppRtAssoc{z}:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref AppSubnet{z}
      RouteTableId: !Ref AppRt{z}

  DataRt{z}:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc
      Tags:
        - Key: Name
          Value: dbws-rt-data-{az}

  DataRtAssoc{z}:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref DataSubnet{z}
      RouteTableId: !Ref DataRt{z}
""")
    return "".join(out)


ENDPOINTS = """
  # ---------------------------------------------------------------- VPC endpoints
  VpcEndpointS3:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref Vpc
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcEndpointType: Gateway
      RouteTableIds: [!Ref AppRtA, !Ref AppRtB, !Ref AppRtC]

  VpcEndpointDynamoDb:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref Vpc
      ServiceName: !Sub com.amazonaws.${AWS::Region}.dynamodb
      VpcEndpointType: Gateway
      RouteTableIds: [!Ref AppRtA, !Ref AppRtB, !Ref AppRtC]

  VpceSg:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: dbws-sg-vpce
      GroupDescription: Interface endpoints - HTTPS and Keyspaces (9142) from the app subnets
      VpcId: !Ref Vpc
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 10.20.10.0/24
          Description: dbws-app-a (HTTPS APIs)
        - IpProtocol: tcp
          FromPort: 9142
          ToPort: 9142
          CidrIp: 10.20.10.0/24
          Description: dbws-app-a (Keyspaces CQL over TLS)
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 10.20.11.0/24
          Description: dbws-app-b (HTTPS APIs)
        - IpProtocol: tcp
          FromPort: 9142
          ToPort: 9142
          CidrIp: 10.20.11.0/24
          Description: dbws-app-b (Keyspaces CQL over TLS)
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 10.20.12.0/24
          Description: dbws-app-c (HTTPS APIs)
        - IpProtocol: tcp
          FromPort: 9142
          ToPort: 9142
          CidrIp: 10.20.12.0/24
          Description: dbws-app-c (Keyspaces CQL over TLS)
      Tags:
        - Key: Name
          Value: dbws-sg-vpce
"""
for name, svc in (("Ssm", "ssm"), ("SsmMessages", "ssmmessages"), ("Ec2Messages", "ec2messages"),
                  ("SecretsManager", "secretsmanager"), ("Keyspaces", "cassandra")):
    ENDPOINTS += f"""
  VpcEndpoint{name}:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref Vpc
      ServiceName: !Sub com.amazonaws.${{AWS::Region}}.{svc}
      VpcEndpointType: Interface
      PrivateDnsEnabled: true
      SubnetIds: [!Ref DataSubnetA, !Ref DataSubnetB, !Ref DataSubnetC]
      SecurityGroupIds: [!Ref VpceSg]
"""

EDGE = r"""
  # ================================================================ Web access: ALB, certificate, DNS
  AlbSg:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: dbws-sg-alb
      GroupDescription: ALB - HTTPS 443 and HTTP 80 (redirect) from AllowedCidr
      VpcId: !Ref Vpc
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: !Ref AllowedCidr
          Description: Participants (HTTPS)
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: !Ref AllowedCidr
          Description: Participants (HTTP, redirected to HTTPS)
      Tags:
        - Key: Name
          Value: dbws-sg-alb

  Certificate:
    Type: AWS::CertificateManager::Certificate
    Properties:
      DomainName: !Ref DomainName
      ValidationMethod: DNS
      DomainValidationOptions:
        - DomainName: !Ref DomainName
          HostedZoneId: !Ref HostedZoneId
      Tags:
        - Key: Name
          Value: dbws-cert

  Alb:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    DependsOn: IgwAttachment
    Properties:
      Name: dbws-alb
      Scheme: internet-facing
      Type: application
      IpAddressType: ipv4
      Subnets: [!Ref PublicSubnetA, !Ref PublicSubnetB, !Ref PublicSubnetC]
      SecurityGroups: [!Ref AlbSg]
      LoadBalancerAttributes:
        - Key: routing.http.drop_invalid_header_fields.enabled
          Value: 'true'
        - Key: idle_timeout.timeout_seconds
          Value: '120'
      Tags:
        - Key: Name
          Value: dbws-alb

  HttpListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref Alb
      Protocol: HTTP
      Port: 80
      DefaultActions:
        - Type: redirect
          RedirectConfig:
            Protocol: HTTPS
            Port: '443'
            StatusCode: HTTP_301

  HttpsListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref Alb
      Protocol: HTTPS
      Port: 443
      SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
      Certificates:
        - CertificateArn: !Ref Certificate
      DefaultActions:
        - Type: fixed-response
          FixedResponseConfig:
            StatusCode: '200'
            ContentType: text/html
            MessageBody: >-
              <html><head><meta charset="utf-8"><title>AWS Database Workshop</title>
              <style>body{font-family:sans-serif;margin:40px}a{display:block;margin:6px 0}</style></head>
              <body><h1>AWS Database Workshop</h1><p>Bir Engine App seçin:</p>
              <a href="/aurora/">Aurora PostgreSQL - Relational</a><a href="/redshift/">Redshift - Columnar</a>
              <a href="/dynamodb/">DynamoDB - Key-value</a><a href="/elasticache/">ElastiCache - In-memory</a>
              <a href="/keyspaces/">Keyspaces - Wide column</a><a href="/influxdb/">InfluxDB - Time-series</a>
              <a href="/neptune/">Neptune - Graph</a><a href="/docdb/">DocumentDB - Document</a>
              <a href="/s3/">S3 - Blob</a><a href="/opensearch/">OpenSearch - Text search + geo</a></body></html>

  DnsRecord:
    Type: AWS::Route53::RecordSet
    Properties:
      HostedZoneId: !Ref HostedZoneId
      Name: !Ref DomainName
      Type: A
      AliasTarget:
        DNSName: !GetAtt Alb.DNSName
        HostedZoneId: !GetAtt Alb.CanonicalHostedZoneID
        EvaluateTargetHealth: false

  AppLaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: dbws-engine-app
      LaunchTemplateData:
        MetadataOptions:
          HttpTokens: required
          HttpEndpoint: enabled
          HttpPutResponseHopLimit: 1
        BlockDeviceMappings:
          - DeviceName: /dev/xvda
            Ebs:
              VolumeSize: 20
              VolumeType: gp3
              Encrypted: true
              DeleteOnTermination: true
        Monitoring:
          Enabled: true
"""

ENGINES = r"""
  # ================================================================ Engines
  # ---------------------------------------------------------------- 1 Aurora PostgreSQL (relational)
  AuroraSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupName: dbws-aurora
      DBSubnetGroupDescription: Aurora - data subnets
      SubnetIds: [!Ref DataSubnetA, !Ref DataSubnetB, !Ref DataSubnetC]

  AuroraCluster:
    Type: AWS::RDS::DBCluster
    DeletionPolicy: Delete
    UpdateReplacePolicy: Delete
    Properties:
      DBClusterIdentifier: dbws-aurora
      Engine: aurora-postgresql
      EngineVersion: '17.9'
      DatabaseName: shop
      MasterUsername: dbwsadmin
      ManageMasterUserPassword: true
      StorageEncrypted: true
      DBSubnetGroupName: !Ref AuroraSubnetGroup
      VpcSecurityGroupIds: [!Ref DbSgAurora]
      ServerlessV2ScalingConfiguration:
        MinCapacity: 0.5
        MaxCapacity: 4
      BackupRetentionPeriod: 1
      DeletionProtection: false
      EnableIAMDatabaseAuthentication: false

  AuroraWriter:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: dbws-aurora-writer
      DBClusterIdentifier: !Ref AuroraCluster
      Engine: aurora-postgresql
      DBInstanceClass: db.serverless
      AvailabilityZone: !Sub ${AWS::Region}a
      PubliclyAccessible: false

  AuroraReader:
    Type: AWS::RDS::DBInstance
    DependsOn: AuroraWriter
    Properties:
      DBInstanceIdentifier: dbws-aurora-reader
      DBClusterIdentifier: !Ref AuroraCluster
      Engine: aurora-postgresql
      DBInstanceClass: db.serverless
      AvailabilityZone: !Sub ${AWS::Region}b
      PubliclyAccessible: false

  # ---------------------------------------------------------------- 2 Redshift Serverless (columnar)
  RedshiftSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: dbws/redshift
      Description: Redshift Serverless admin user for the Redshift Engine App
      GenerateSecretString:
        SecretStringTemplate: '{"username":"dbwsadmin"}'
        GenerateStringKey: password
        PasswordLength: 32
        ExcludePunctuation: true
        RequireEachIncludedType: true

  RedshiftNamespace:
    Type: AWS::RedshiftServerless::Namespace
    Properties:
      NamespaceName: dbws
      DbName: dev
      AdminUsername: dbwsadmin
      AdminUserPassword: !Sub '{{resolve:secretsmanager:${RedshiftSecret}:SecretString:password}}'

  RedshiftWorkgroup:
    Type: AWS::RedshiftServerless::Workgroup
    Properties:
      WorkgroupName: dbws
      NamespaceName: !Ref RedshiftNamespace
      BaseCapacity: 8
      PubliclyAccessible: false
      EnhancedVpcRouting: true
      SubnetIds: [!Ref DataSubnetA, !Ref DataSubnetB, !Ref DataSubnetC]
      SecurityGroupIds: [!Ref DbSgRedshift]

  # ---------------------------------------------------------------- 3 DynamoDB (key-value)
  CartTable:
    Type: AWS::DynamoDB::Table
    DeletionPolicy: Delete
    UpdateReplacePolicy: Delete
    Properties:
      TableName: dbws-cart
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: pk
          AttributeType: S
        - AttributeName: sk
          AttributeType: S
      KeySchema:
        - AttributeName: pk
          KeyType: HASH
        - AttributeName: sk
          KeyType: RANGE
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      SSESpecification:
        SSEEnabled: true

  # ---------------------------------------------------------------- 4 ElastiCache Serverless Valkey (in-memory)
  CacheUserSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: dbws/elasticache
      Description: ElastiCache user for the ElastiCache Engine App
      GenerateSecretString:
        SecretStringTemplate: '{"username":"dbws-app"}'
        GenerateStringKey: password
        PasswordLength: 32
        ExcludePunctuation: true
        RequireEachIncludedType: true

  CacheAppUser:
    Type: AWS::ElastiCache::User
    Properties:
      UserId: dbws-app
      UserName: dbws-app
      Engine: valkey
      AccessString: on ~* +@all -@dangerous
      AuthenticationMode:
        Type: password
        Passwords:
          - !Sub '{{resolve:secretsmanager:${CacheUserSecret}:SecretString:password}}'

  CacheUserGroup:
    Type: AWS::ElastiCache::UserGroup
    Properties:
      UserGroupId: dbws-users
      Engine: valkey
      UserIds: [!Ref CacheAppUser]

  Cache:
    Type: AWS::ElastiCache::ServerlessCache
    Properties:
      ServerlessCacheName: dbws-cache
      Engine: valkey
      MajorEngineVersion: '8'
      UserGroupId: !Ref CacheUserGroup
      SubnetIds: [!Ref DataSubnetA, !Ref DataSubnetB, !Ref DataSubnetC]
      SecurityGroupIds: [!Ref DbSgElastiCache]

  # ---------------------------------------------------------------- 5 Keyspaces (wide column)
  ActivityKeyspace:
    Type: AWS::Cassandra::Keyspace
    Properties:
      KeyspaceName: dbws

  ActivityTable:
    Type: AWS::Cassandra::Table
    Properties:
      KeyspaceName: !Ref ActivityKeyspace
      TableName: activity_by_user
      PartitionKeyColumns:
        - ColumnName: user_id
          ColumnType: text
      ClusteringKeyColumns:
        - Column:
            ColumnName: event_time
            ColumnType: timestamp
          OrderBy: DESC
        - Column:
            ColumnName: event_id
            ColumnType: uuid
          OrderBy: ASC
      RegularColumns:
        - ColumnName: event_type
          ColumnType: text
        - ColumnName: product_id
          ColumnType: text
        - ColumnName: detail
          ColumnType: text
      BillingMode:
        Mode: ON_DEMAND
      PointInTimeRecoveryEnabled: true

  # ---------------------------------------------------------------- 6 Timestream for InfluxDB (time-series)
  InfluxDbSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: dbws/influxdb
      Description: InfluxDB admin user for the InfluxDB Engine App
      GenerateSecretString:
        SecretStringTemplate: '{"username":"dbwsadmin"}'
        GenerateStringKey: password
        PasswordLength: 32
        ExcludePunctuation: true
        RequireEachIncludedType: true

  InfluxDb:
    Type: AWS::Timestream::InfluxDBInstance
    Properties:
      Name: dbws-influxdb
      DbInstanceType: db.influx.medium
      DbStorageType: InfluxIOIncludedT1
      AllocatedStorage: 20
      DeploymentType: WITH_MULTIAZ_STANDBY
      Username: dbwsadmin
      Password: !Sub '{{resolve:secretsmanager:${InfluxDbSecret}:SecretString:password}}'
      Organization: dbws
      Bucket: metrics
      PubliclyAccessible: false
      VpcSubnetIds: [!Ref DataSubnetA, !Ref DataSubnetB, !Ref DataSubnetC]
      VpcSecurityGroupIds: [!Ref DbSgInfluxDb]

  # ---------------------------------------------------------------- 7 Neptune (graph)
  NeptuneSubnetGroup:
    Type: AWS::Neptune::DBSubnetGroup
    Properties:
      DBSubnetGroupName: dbws-neptune
      DBSubnetGroupDescription: Neptune - data subnets
      SubnetIds: [!Ref DataSubnetA, !Ref DataSubnetB, !Ref DataSubnetC]

  NeptuneCluster:
    Type: AWS::Neptune::DBCluster
    DeletionPolicy: Delete
    UpdateReplacePolicy: Delete
    Properties:
      DBClusterIdentifier: dbws-neptune
      DBSubnetGroupName: !Ref NeptuneSubnetGroup
      VpcSecurityGroupIds: [!Ref DbSgNeptune]
      IamAuthEnabled: true
      StorageEncrypted: true
      DeletionProtection: false
      BackupRetentionPeriod: 1
      ServerlessScalingConfiguration:
        MinCapacity: 1
        MaxCapacity: 8

  NeptuneWriter:
    Type: AWS::Neptune::DBInstance
    Properties:
      DBInstanceIdentifier: dbws-neptune-writer
      DBClusterIdentifier: !Ref NeptuneCluster
      DBInstanceClass: db.serverless
      AvailabilityZone: !Sub ${AWS::Region}b

  NeptuneReader:
    Type: AWS::Neptune::DBInstance
    DependsOn: NeptuneWriter
    Properties:
      DBInstanceIdentifier: dbws-neptune-reader
      DBClusterIdentifier: !Ref NeptuneCluster
      DBInstanceClass: db.serverless
      AvailabilityZone: !Sub ${AWS::Region}c

  # ---------------------------------------------------------------- 8 DocumentDB (document)
  DocDbSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: dbws/docdb
      Description: DocumentDB admin user for the DocumentDB Engine App
      GenerateSecretString:
        SecretStringTemplate: '{"username":"dbwsadmin"}'
        GenerateStringKey: password
        PasswordLength: 32
        ExcludePunctuation: true
        RequireEachIncludedType: true

  DocDbSubnetGroup:
    Type: AWS::DocDB::DBSubnetGroup
    Properties:
      DBSubnetGroupName: dbws-docdb
      DBSubnetGroupDescription: DocumentDB - data subnets
      SubnetIds: [!Ref DataSubnetA, !Ref DataSubnetB, !Ref DataSubnetC]

  DocDbCluster:
    Type: AWS::DocDB::DBCluster
    DeletionPolicy: Delete
    UpdateReplacePolicy: Delete
    Properties:
      DBClusterIdentifier: dbws-docdb
      EngineVersion: 8.0.0
      MasterUsername: dbwsadmin
      MasterUserPassword: !Sub '{{resolve:secretsmanager:${DocDbSecret}:SecretString:password}}'
      DBSubnetGroupName: !Ref DocDbSubnetGroup
      VpcSecurityGroupIds: [!Ref DbSgDocDb]
      StorageEncrypted: true
      DeletionProtection: false
      BackupRetentionPeriod: 1

  DocDbPrimary:
    Type: AWS::DocDB::DBInstance
    Properties:
      DBInstanceIdentifier: dbws-docdb-1
      DBClusterIdentifier: !Ref DocDbCluster
      DBInstanceClass: db.r6g.large
      AvailabilityZone: !Sub ${AWS::Region}b

  DocDbReplica:
    Type: AWS::DocDB::DBInstance
    DependsOn: DocDbPrimary
    Properties:
      DBInstanceIdentifier: dbws-docdb-2
      DBClusterIdentifier: !Ref DocDbCluster
      DBInstanceClass: db.r6g.large
      AvailabilityZone: !Sub ${AWS::Region}c

  # ---------------------------------------------------------------- 9 S3 (blob)
  ImageBucket:
    Type: AWS::S3::Bucket
    DeletionPolicy: Delete
    UpdateReplacePolicy: Delete
    Properties:
      BucketName: !Sub dbws-images-${AWS::AccountId}-${AWS::Region}
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      OwnershipControls:
        Rules:
          - ObjectOwnership: BucketOwnerEnforced
      LifecycleConfiguration:
        Rules:
          - Id: expire-old-versions
            Status: Enabled
            NoncurrentVersionExpiration:
              NoncurrentDays: 1

  ImageBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref ImageBucket
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Sid: DenyInsecureTransport
            Effect: Deny
            Principal: '*'
            Action: s3:*
            Resource:
              - !GetAtt ImageBucket.Arn
              - !Sub ${ImageBucket.Arn}/*
            Condition:
              Bool:
                aws:SecureTransport: 'false'

  # Empties the versioned bucket when the stack is deleted, so the delete does not fail.
  BucketCleanerRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - !Sub arn:${AWS::Partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: empty-bucket
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action: [s3:ListBucket, s3:ListBucketVersions]
                Resource: !GetAtt ImageBucket.Arn
              - Effect: Allow
                Action: [s3:DeleteObject, s3:DeleteObjectVersion]
                Resource: !Sub ${ImageBucket.Arn}/*

  BucketCleanerFunction:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: python3.13
      Handler: index.handler
      Timeout: 300
      Role: !GetAtt BucketCleanerRole.Arn
      Code:
        ZipFile: |
          import boto3, cfnresponse
          def handler(event, context):
              try:
                  if event["RequestType"] == "Delete":
                      b = boto3.resource("s3").Bucket(event["ResourceProperties"]["BucketName"])
                      b.object_versions.delete()
                  cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
              except Exception as e:
                  print(e)
                  cfnresponse.send(event, context, cfnresponse.FAILED, {"Error": str(e)})

  BucketCleaner:
    Type: Custom::EmptyBucket
    Properties:
      ServiceToken: !GetAtt BucketCleanerFunction.Arn
      BucketName: !Ref ImageBucket

  # ---------------------------------------------------------------- 10 OpenSearch Service (text search + geo)
  OpenSearchServiceLinkedRole:
    Type: AWS::IAM::ServiceLinkedRole
    Condition: CreateOsSlr
    Properties:
      AWSServiceName: opensearchservice.amazonaws.com

  SearchDomain:
    Type: AWS::OpenSearchService::Domain
    Metadata:
      # implicit dependency on the service-linked role when this stack creates it
      ServiceLinkedRole: !If [CreateOsSlr, !Ref OpenSearchServiceLinkedRole, none]
    Properties:
      DomainName: dbws-search
      EngineVersion: OpenSearch_3.5
      ClusterConfig:
        InstanceType: r6g.large.search
        InstanceCount: 3
        ZoneAwarenessEnabled: true
        ZoneAwarenessConfig:
          AvailabilityZoneCount: 3
        DedicatedMasterEnabled: true
        DedicatedMasterType: m6g.large.search
        DedicatedMasterCount: 3
      EBSOptions:
        EBSEnabled: true
        VolumeType: gp3
        VolumeSize: 20
      VPCOptions:
        SubnetIds: [!Ref DataSubnetA, !Ref DataSubnetB, !Ref DataSubnetC]
        SecurityGroupIds: [!Ref DbSgOpenSearch]
      EncryptionAtRestOptions:
        Enabled: true
      NodeToNodeEncryptionOptions:
        Enabled: true
      DomainEndpointOptions:
        EnforceHTTPS: true
        TLSSecurityPolicy: Policy-Min-TLS-1-2-PFS-2023-10
      AdvancedSecurityOptions:
        Enabled: true
        InternalUserDatabaseEnabled: false
        MasterUserOptions:
          MasterUserARN: !GetAtt AppRoleOpenSearch.Arn
      AccessPolicies:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !GetAtt AppRoleOpenSearch.Arn
            Action: es:ESHttp*
            Resource: !Sub arn:${AWS::Partition}:es:${AWS::Region}:${AWS::AccountId}:domain/dbws-search/*
"""

OUTPUTS = """
Outputs:
  WorkshopUrl:
    Description: Dashboard with links to all Engine Apps
    Value: !Sub https://${DomainName}/
  AlbDnsName:
    Value: !GetAtt Alb.DNSName
  VpcId:
    Value: !Ref Vpc
"""
for eid, label, *_ in APPS:
    OUTPUTS += f"""  {cap(eid)}AppUrl:
    Description: {label} Engine App
    Value: !Sub https://${{DomainName}}/{eid}/
"""

yaml = HEADER + network() + ENDPOINTS + EDGE + ENGINES + app_blocks() + OUTPUTS
open(OUT, "w").write(yaml)
print("written", OUT, len(yaml), "bytes")
