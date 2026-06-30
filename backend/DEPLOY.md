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

> Read **../SECURITY.md** first — this deploy assumes a private bucket,
> Firestore, Firebase Auth, and a dedicated least-privilege service account.

### 1. Set up GCP project

```bash
export PROJECT_ID=your-gcp-project-id
export GCS_BUCKET=$PROJECT_ID-uploads
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  identitytoolkit.googleapis.com
```

### 2. Firebase Auth

1. In the [Firebase console](https://console.firebase.google.com), add Firebase
   to this same GCP project.
2. Authentication → Sign-in method → enable **Google** (and optionally
   Email/Password). Restrict signups if using Google only.
3. Project settings → Your apps → Web app → copy the config into the frontend's
   `VITE_FIREBASE_*` env vars.

### 3. Private bucket + Firestore

```bash
# Private bucket (uniform access + public access prevention)
gsutil mb -b on -l us-central1 gs://$GCS_BUCKET
gsutil pap set enforced gs://$GCS_BUCKET

# Firestore in Native mode (once per project)
gcloud firestore databases create --location=us-central1
```

### 4. Dedicated runtime service account (least privilege)

```bash
gcloud iam service-accounts create lab-backend-sa \
  --display-name="Lab backend runtime"

gsutil iam ch \
  serviceAccount:lab-backend-sa@$PROJECT_ID.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://$GCS_BUCKET

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:lab-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### 5. Deploy to Cloud Run

```bash
gcloud run deploy lab-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --service-account lab-backend-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 3600 \
  --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET=$GCS_BUCKET,ALLOWED_EMAILS=you@example.com"
```

Notes:
- `--allow-unauthenticated` exposes the *port*, but every data endpoint still
  requires a valid Firebase token + allowlisted email. Only `/` (health) is open.
- Update `ALLOWED_EMAILS` (comma-separated) to invite/revoke team members.
- Builds the image, pushes to Artifact Registry, deploys with the locked-down SA.

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

Set on deploy via `--set-env-vars` (see step 5). See `.env.example` for the
full list:
- `GCP_PROJECT_ID` — project owning the bucket + Firestore
- `GCS_BUCKET` — private uploads bucket
- `ALLOWED_EMAILS` — comma-separated invite allowlist
- `ALLOWED_ORIGINS` — optional extra CORS origins (localhost + `*.vercel.app` already allowed)

## Important Notes

### File Storage
✅ Files are stored in a **private GCS bucket** and metadata in **Firestore**, so
data survives restarts/redeploys. Nothing on the container disk is persisted —
that's intentional. Bytes are only served through the authenticated
`/download/{file_id}` endpoint; the bucket itself stays private.

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
