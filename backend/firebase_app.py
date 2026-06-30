"""Single Firebase Admin initialization shared across the backend.

On Cloud Run this uses the service account's Application Default
Credentials automatically. Locally, run:

    gcloud auth application-default login
    export GOOGLE_CLOUD_PROJECT=<your-project-id>
"""
import firebase_admin

if not firebase_admin._apps:
    firebase_admin.initialize_app()
