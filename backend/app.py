from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import uuid
from pathlib import Path
from typing import Optional

import firebase_app  # noqa: F401  (initializes Firebase Admin on import)
from auth import get_current_user
from config import ALLOWED_ORIGINS, VERCEL_ORIGIN_REGEX
import storage
import db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=VERCEL_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_PREFIX = "uploads/"
IMAGE_PREFIX = "collection_images/"


@app.get("/")
def health():
    """Public, unauthenticated health check (no data)."""
    return {"status": "ok"}


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


@app.get("/collections")
def list_collections(user: dict = Depends(get_current_user)):
    return db.list_collections()


@app.post("/collections")
async def create_collection(
    name: str = Form(...),
    image: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    image_path = None
    if image is not None and image.filename:
        unique_id = uuid.uuid4().hex[:8]
        ext = Path(image.filename).suffix
        image_path = f"{IMAGE_PREFIX}{Path(image.filename).stem}_{unique_id}{ext}"
        storage.upload_fileobj(image_path, image.file, image.content_type)

    collection = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "image": image_path,
        "created_by": user["email"],
    }
    db.add_collection(collection)
    return collection


@app.get("/collection-image/{collection_id}")
def get_collection_image(collection_id: str, user: dict = Depends(get_current_user)):
    collection = db.get_collection(collection_id)
    if not collection or not collection.get("image"):
        raise HTTPException(status_code=404, detail="Image not found")
    data = storage.download_bytes(collection["image"])
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=data, media_type="application/octet-stream")


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    collection_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    if collection_id and db.get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    unique_id = uuid.uuid4().hex[:8]
    original_filename = file.filename
    stem = Path(original_filename).stem
    ext = Path(original_filename).suffix
    stored_filename = f"{stem}_{unique_id}{ext}"
    gcs_path = f"{UPLOAD_PREFIX}{stored_filename}"

    storage.upload_fileobj(gcs_path, file.file, file.content_type)

    file_entry = {
        "id": unique_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "gcs_path": gcs_path,
        "content_type": file.content_type or "application/octet-stream",
        "collection_id": collection_id,
        "owner": user["email"],
    }
    db.add_file(file_entry)
    return file_entry


@app.get("/files")
def list_files(
    collection_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    return db.list_files(collection_id)


@app.get("/download/{file_id}")
def download_file(file_id: str, user: dict = Depends(get_current_user)):
    entry = db.get_file(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    data = storage.download_bytes(entry["gcs_path"])
    if data is None:
        raise HTTPException(status_code=404, detail="File not found")

    return Response(
        content=data,
        media_type=entry.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{entry["original_filename"]}"'
        },
    )


@app.put("/files/{file_id}")
async def update_file_content(
    file_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Overwrite the stored bytes of a file (used to save edits)."""
    entry = db.get_file(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    storage.upload_fileobj(entry["gcs_path"], file.file, entry.get("content_type"))
    return entry


@app.delete("/files/{file_id}")
def delete_file(file_id: str, user: dict = Depends(get_current_user)):
    entry = db.get_file(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    storage.delete_blob(entry["gcs_path"])
    db.delete_file(file_id)
    return {"message": "File deleted successfully"}
