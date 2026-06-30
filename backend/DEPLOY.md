# Backend Deployment Guide

This guide covers deploying the FastAPI backend to Google Cloud Run.

## Prerequisites

- Google Cloud Project created
- `gcloud` CLI installed and authenticated
- Docker installed (for local testing)

## Local Testing with Docker

Build and run locally:

```bash
docker build -t lab-backend .
docker run -p 8080:8080 lab-backend
```

Then visit `http://localhost:8080` and test endpoints.

## Deploy to GCP Cloud Run

### 1. Set up GCP project

```bash
# Set your project ID
export PROJECT_ID=your-gcp-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 2. Create Artifact Registry (for container images)

```bash
gcloud artifacts repositories create cloud-run-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Cloud Run images"
```

### 3. Deploy directly to Cloud Run

```bash
gcloud run deploy lab-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 3600
```

This command:
- Builds the Docker image automatically
- Pushes to Artifact Registry
- Deploys to Cloud Run
- Allows unauthenticated access (so frontend can call it)
- Allocates 512MB RAM and 1 CPU
- 1-hour timeout for operations

**Note:** First deployment takes 1-2 minutes. Output will show your service URL: `https://lab-backend-xxxxx.run.app`

### 4. View logs

```bash
gcloud run logs read lab-backend --region us-central1 --limit 50
```

### 5. Monitor and manage

```bash
# View service details
gcloud run services describe lab-backend --region us-central1

# View all deployments
gcloud run services list --region us-central1

# Update service (re-deploy)
gcloud run deploy lab-backend --source . --region us-central1 --platform managed --allow-unauthenticated
```

## Environment Variables

Currently, the backend doesn't need environment variables. If you add them later:

```bash
gcloud run deploy lab-backend \
  --source . \
  --region us-central1 \
  --set-env-vars KEY=value
```

## Important Notes

### File Storage
⚠️ Cloud Run's filesystem is **ephemeral** — files in `/app/uploads/` and `/app/data.json` are deleted when the service restarts.

**For production persistence, you need to:**
1. Use Google Cloud Storage (GCS) for uploads
2. Use Cloud Datastore or Firestore for data.json

For now, this limitation is acceptable for testing.

### Quotas & Pricing
- Free tier: 2 million requests/month
- Compute: $0.00001667 per CPU-second
- Memory: $0.0000025 per GB-second
- Your small app likely stays free

### CORS
The backend is configured to accept requests from:
- `http://localhost:*` (local development)
- `https://*.vercel.app` (Vercel deployments)

Update `app.py` CORS config if needed.

## Troubleshooting

**Deployment fails:**
```bash
gcloud run deploy lab-backend --source . --region us-central1 --allow-unauthenticated --log-http
```

**Service returns 502 Bad Gateway:**
- Check logs: `gcloud run logs read lab-backend`
- Verify port is 8080 in Dockerfile
- Check memory allocation isn't too low

**Can't access service:**
- Verify `--allow-unauthenticated` flag was used
- Check CORS origins in `app.py`
- Verify frontend is using correct Cloud Run URL
