# QmanAssist - Docker Deployment Guide

This guide explains how to deploy QmanAssist using Docker Desktop with optimized resource allocation.

## Prerequisites

- Docker Desktop installed (Windows/Mac/Linux)
- At least 8GB RAM available for Docker
- Access to Q:\ drive or network share with documents

## Quick Start

### 1. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Required: API Keys
OPENAI_API_KEY=sk-your-openai-key-here
# or
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Required: LLM Provider
LLM_PROVIDER=openai

# Required: Document Path
# For Windows Docker Desktop with Q:\ drive:
QMANUALS_HOST_PATH=Q:\
# For Linux/WSL with mounted share:
QMANUALS_HOST_PATH=/mnt/q
```

### 2. Build and Run

```bash
# Build the container
docker-compose build

# Start QmanAssist
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access the Application

Open your browser to: **http://localhost:8501**

## Resource Configuration

### Docker Desktop Settings

**Recommended Settings:**
- **CPUs:** 4-6 cores
- **Memory:** 8GB
- **Swap:** 2GB
- **Disk:** 20GB minimum

**To configure in Docker Desktop:**
1. Open Docker Desktop
2. Go to Settings → Resources
3. Adjust CPU, Memory, and Swap
4. Click "Apply & Restart"

### Container Resource Limits

Edit `docker-compose.yml` to adjust limits:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Maximum CPU cores
      memory: 8G       # Maximum RAM
    reservations:
      cpus: '2.0'      # Minimum guaranteed CPUs
      memory: 4G       # Minimum guaranteed RAM
```

## Document Ingestion

### Initial Document Load

Once the container is running, ingest documents:

```bash
# Basic ingestion with default settings (4 workers)
docker-compose exec qmanassist python scripts/ingest_documents.py

# High-performance ingestion (8 workers)
docker-compose exec qmanassist python scripts/ingest_documents.py --workers 8

# Test with limited documents
docker-compose exec qmanassist python scripts/ingest_documents.py --limit 10
```

### Ingestion Performance

With Docker Desktop (4-8 cores):
- **4 workers:** ~100-200 documents/minute
- **8 workers:** ~200-400 documents/minute

Performance depends on:
- Document types (PDFs slower than DOCX)
- Network speed (Q:\ drive access)
- CPU cores allocated
- API rate limits

## Volume Management

### Persistent Data

QmanAssist uses Docker volumes for data persistence:

```bash
# View volumes
docker volume ls

# Inspect ChromaDB data volume
docker volume inspect qmanassist_chroma_data

# Backup ChromaDB data
docker run --rm -v qmanassist_chroma_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/chroma_backup.tar.gz -C /data .

# Restore ChromaDB data
docker run --rm -v qmanassist_chroma_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/chroma_backup.tar.gz -C /data
```

### Document Access

**Windows with Q:\ Drive:**

Edit `docker-compose.yml`:
```yaml
volumes:
  - Q:\:/data/qmanuals:ro
```

Or set in `.env`:
```bash
QMANUALS_HOST_PATH=Q:\
```

**Linux/WSL with Mounted Share:**

```bash
# Mount the share first
sudo mount -t cifs //neonas-01/qmanuals /mnt/q -o username=youruser

# Then in .env:
QMANUALS_HOST_PATH=/mnt/q
```

**SMB Network Path (no mount required):**

Set in `.env`:
```bash
QMANUALS_NETWORK_PATH=//neonas-01/qmanuals
SMB_USERNAME=your_username
SMB_PASSWORD=your_password
SMB_DOMAIN=your_domain
```

## Performance Tuning

### Ingestion Performance

Edit `.env` to tune ingestion:

```bash
# More workers = faster ingestion (requires more CPU)
INGESTION_WORKERS=8

# Larger batches = fewer DB writes (requires more memory)
INGESTION_BATCH_SIZE=100
```

### Application Performance

```bash
# Increase retrieval results
TOP_K=10

# Adjust similarity threshold (lower = more results)
SIMILARITY_THRESHOLD=0.3

# Use faster LLM model
LLM_MODEL=gpt-3.5-turbo
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs qmanassist

# Check resource usage
docker stats qmanassist

# Restart container
docker-compose restart
```

### Memory Issues

If you see OOM (Out of Memory) errors:

1. Increase Docker Desktop memory limit
2. Reduce `INGESTION_WORKERS` in `.env`
3. Reduce `INGESTION_BATCH_SIZE` in `.env`
4. Lower container memory limit in `docker-compose.yml`

### Slow Performance

**If ingestion is slow:**
- Increase `INGESTION_WORKERS` (up to number of CPU cores)
- Increase Docker CPU allocation
- Check network speed to Q:\ drive

**If UI is slow:**
- Increase Docker memory allocation
- Reduce `TOP_K` (fewer documents retrieved)
- Use faster LLM model (gpt-3.5-turbo vs gpt-4)
- Check if container is CPU/memory constrained: `docker stats`

### Network Path Issues

```bash
# Test network access from inside container
docker-compose exec qmanassist ls /data/qmanuals

# For SMB paths, check credentials
docker-compose exec qmanassist python -c "
from src.utils.network_utils import validate_network_access
print(validate_network_access())
"
```

## Maintenance

### Update Application

```bash
# Pull latest code
git pull

# Rebuild container
docker-compose build

# Restart with new version
docker-compose up -d
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes (WARNING: deletes all data)
docker-compose down -v

# Clean up Docker system
docker system prune -a
```

### Monitor Resources

```bash
# Real-time stats
docker stats qmanassist

# Container resource usage over time
docker stats --no-stream qmanassist
```

## Production Deployment

### Security Considerations

1. **Never commit `.env` file with real API keys**
2. Use Docker secrets for sensitive data
3. Run container as non-root user
4. Use read-only volumes where possible
5. Enable Docker Content Trust

### Scaling

For production with high load:

```yaml
# docker-compose.yml
services:
  qmanassist:
    deploy:
      replicas: 3  # Run 3 instances
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

Add a load balancer (nginx, traefik) in front.

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review this documentation
3. Check Docker Desktop resource allocation
4. Verify API keys and environment variables

## Summary

**Basic Commands:**
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f

# Rebuild
docker-compose build

# Ingest docs
docker-compose exec qmanassist python scripts/ingest_documents.py

# Stats
docker stats qmanassist
```

**Recommended Docker Desktop Settings:**
- CPUs: 4-6
- Memory: 8GB
- Swap: 2GB

**Environment Variables to Set:**
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- `LLM_PROVIDER`
- `QMANUALS_HOST_PATH`
- `INGESTION_WORKERS=4-8`
