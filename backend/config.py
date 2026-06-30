import os

# GCP project that owns the GCS bucket and Firestore database.
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")

# Private GCS bucket where all uploaded file bytes live.
# Must have public access prevention enabled (see SECURITY.md).
GCS_BUCKET = os.environ.get("GCS_BUCKET", "")

# Invite-only allowlist. Only these (verified) emails may use the API.
# Comma-separated, e.g. "alice@example.com,bob@example.com".
ALLOWED_EMAILS = [
    e.strip().lower()
    for e in os.environ.get("ALLOWED_EMAILS", "").split(",")
    if e.strip()
]

# Browser origins allowed to call the API (CORS).
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if o.strip()
]

# Any Vercel preview/production deployment is allowed via this regex.
VERCEL_ORIGIN_REGEX = r"https://.*\.vercel\.app"
