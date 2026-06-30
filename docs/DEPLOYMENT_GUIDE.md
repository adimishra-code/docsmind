# Deployment Guide (Version 1.0)

DocsMind supports Docker Compose for rapid deployment on single VMs (e.g., EC2, DigitalOcean Droplet).

## Prerequisites
- Docker and Docker Compose installed.
- Domain name pointed to the server IP.
- At least 4GB RAM (8GB recommended for production loads).

## 1. Prepare the Environment
Clone the repository to your production server:
```bash
git clone https://github.com/your-org/docsmind.git
cd docsmind
```

Copy the example environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file and strictly set secure passwords and a complex `SECRET_KEY`. Include your `OPENAI_API_KEY`.

## 2. Start the Stack
Bring up the entire stack using the production compose file in detached mode:
```bash
docker-compose -f docker-compose.prod.yml up -d
```
This provisions:
- Nginx (Ports 80/443)
- React Frontend (Internal)
- FastAPI Backend (Internal)
- Celery Worker & Beat (Internal)
- PostgreSQL, Redis, Qdrant (Internal)

## 3. Database Migrations
Before the system can be used, the database schema must be applied:
```bash
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## 4. HTTPS / SSL (Optional but Required for Prod)
To enable HTTPS, you must configure Nginx with SSL certificates. We recommend using Certbot:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## 5. Verify Health
Ensure all services are running and healthy:
```bash
docker-compose -f docker-compose.prod.yml ps
```
Visit `http://yourdomain.com/api/health` to confirm the backend is responding.
