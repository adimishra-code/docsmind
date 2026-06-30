# Cloud Deployment Architecture

DocsMind Version 1.0 is container-native and designed to be deployed across any major cloud provider (AWS, Azure, GCP).

## 1. Amazon Web Services (AWS)

### Architecture
- **Compute**: Amazon ECS with AWS Fargate (Serverless Containers).
- **Database**: Amazon RDS for PostgreSQL (Multi-AZ).
- **Cache & Broker**: Amazon ElastiCache (Redis).
- **Vector DB**: Qdrant Cloud on AWS, or self-hosted Qdrant on EC2 (r6i instances).
- **Storage**: Amazon S3 (for document blob storage).
- **Networking**: Application Load Balancer (ALB) terminating SSL.
- **Secrets**: AWS Secrets Manager.

### Cost Estimation (Baseline Prod)
- Fargate (3 services x 2 tasks): ~$150/mo
- RDS (db.t4g.medium): ~$60/mo
- ElastiCache (cache.t4g.small): ~$16/mo
- S3 & Bandwidth: ~$20/mo
- **Total**: ~$246/month

## 2. Microsoft Azure

### Architecture
- **Compute**: Azure Container Apps.
- **Database**: Azure Database for PostgreSQL Flexible Server.
- **Cache & Broker**: Azure Cache for Redis.
- **Vector DB**: Qdrant Cloud on Azure.
- **Storage**: Azure Blob Storage.
- **Networking**: Azure Front Door / Application Gateway.
- **Secrets**: Azure Key Vault.

## 3. Google Cloud Platform (GCP)

### Architecture
- **Compute**: Google Cloud Run (Fully managed).
- **Database**: Cloud SQL for PostgreSQL.
- **Cache & Broker**: Memorystore for Redis.
- **Vector DB**: Qdrant Cloud on GCP.
- **Storage**: Google Cloud Storage (GCS).
- **Networking**: Global HTTP(S) Load Balancer.
- **Secrets**: Google Secret Manager.

## 4. Kubernetes Migration Path
While the v1.0 target uses managed container runtimes (ECS, Cloud Run, Container Apps), the Dockerfiles and stateless backend design ensure a 1:1 migration path to Kubernetes (EKS/AKS/GKE). 

### Required Manifests for Future K8s
- `Deployment` (Backend, Worker, Frontend)
- `Service` (ClusterIP for internal routing)
- `Ingress` (NGINX Ingress Controller)
- `ConfigMap` / `Secret` (Environment variables)
- `HorizontalPodAutoscaler` (CPU/Memory scaling)
