# Security Model

This app is built for an **invite-only team** with **no publicly accessible
documents**. Security is layered (defense-in-depth) — not a single switch.

> Honest scope: no system is "leak-proof." This design removes the obvious
> leak paths (open endpoints, public buckets, over-privileged accounts) and
> makes access auditable. Operational discipline (MFA, least privilege, key
> hygiene) is what keeps it secure over time.

## Layers

### 1. Authentication — Firebase Auth
- Every protected endpoint requires `Authorization: Bearer <Firebase ID token>`.
- The backend cryptographically verifies the token on each request
  (`firebase_admin.auth.verify_id_token`). No valid token → `401`.
- The token's email must be **verified** (`email_verified`) → otherwise `403`.

### 2. Authorization — invite-only allowlist
- The verified email must be in `ALLOWED_EMAILS` (backend env var) → else `403`.
- Signing in is not enough; an account only gains access if you added its email.
- To revoke someone: remove their email and redeploy. To add: append + redeploy.

### 3. Documents — private GCS bucket
- All file bytes live in one GCS bucket with **Public Access Prevention** on and
  **uniform bucket-level access** enabled. No object is ever made public.
- Bytes are only ever returned through the authenticated `/download/{file_id}`
  endpoint — there are no public or signed-URL links handed to the browser.

### 4. Metadata — Firestore
- Collections/file index live in Firestore (the persistent source of truth),
  replacing the old ephemeral `data.json`.
- Lock Firestore down with Security Rules so only the backend service account
  reads/writes it (clients never talk to Firestore directly — see below).

## GCP hardening checklist

**Dedicated runtime service account (least privilege).** Do NOT use the default
Compute service account. Create one just for this service:

```bash
gcloud iam service-accounts create lab-backend-sa \
  --display-name="Lab backend runtime"

# GCS: object read/write on the bucket only
gsutil iam ch \
  serviceAccount:lab-backend-sa@$PROJECT_ID.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://$GCS_BUCKET

# Firestore access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:lab-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

Deploy Cloud Run with `--service-account lab-backend-sa@...` (see DEPLOY.md).

**Private bucket.**
```bash
gsutil mb -b on -l us-central1 gs://$GCS_BUCKET          # uniform access
gsutil pap set enforced gs://$GCS_BUCKET                  # public access prevention
```

**Account security.**
- Enforce **MFA / 2-Step Verification** on every Google account with access
  (both app users and GCP console admins).
- Restrict `roles/owner` and billing-admin to the fewest people possible.
- Prefer Google sign-in for app users (emails are pre-verified).
- In the Firebase console, restrict or disable self-serve email/password signup
  if you only use Google sign-in.

**Keys & secrets.**
- On Cloud Run, use the attached service account (Application Default
  Credentials) — do **not** ship a service-account JSON key in the image.
- Never commit `.env` / `.env.local` (already gitignored).
- Firebase *web* config values (apiKey, etc.) are not secrets; real protection
  is the backend allowlist + bucket/Firestore rules, not hiding those values.

**Network / CORS.**
- CORS allows only localhost + your `*.vercel.app` origins (configurable).
- The only unauthenticated route is `/` (a health check that returns no data).

## Threat notes
- Stolen ID token: short-lived (~1h) and re-verified server-side; remove the
  user from the allowlist to cut access immediately.
- Bucket enumeration: blocked by Public Access Prevention + no public links.
- Privilege escalation: contained by the dedicated least-privilege SA.
