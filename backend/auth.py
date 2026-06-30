"""Authentication + authorization for every protected endpoint.

Each request must carry a Firebase ID token: `Authorization: Bearer <token>`.
The token is cryptographically verified, the email must be verified, and the
email must be on the invite-only allowlist. Any failure → 401/403.
"""
import firebase_app  # noqa: F401  (initializes Firebase Admin on import)

from firebase_admin import auth as fb_auth
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import ALLOWED_EMAILS

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        decoded = fb_auth.verify_id_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    email = (decoded.get("email") or "").lower()

    if not decoded.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")

    if not email or email not in ALLOWED_EMAILS:
        raise HTTPException(status_code=403, detail="Account not authorized")

    return {"uid": decoded["uid"], "email": email}
