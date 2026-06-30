from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import shutil
import uuid
from pathlib import Path
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
COLLECTION_IMAGE_DIR = Path("collection_images")
DATA_FILE = Path("data.json")

UPLOAD_DIR.mkdir(exist_ok=True)
COLLECTION_IMAGE_DIR.mkdir(exist_ok=True)


def load_data():
    if not DATA_FILE.exists():
        return {"collections": [], "files": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


@app.get("/")
def read_root():
    return {"message": "File Upload API"}


@app.get("/collections")
def list_collections():
    data = load_data()
    return data["collections"]


@app.post("/collections")
async def create_collection(name: str = Form(...), image: Optional[UploadFile] = File(None)):
    data = load_data()

    image_filename = None
    if image is not None and image.filename:
        unique_id = uuid.uuid4().hex[:8]
        ext = Path(image.filename).suffix
        image_filename = f"{Path(image.filename).stem}_{unique_id}{ext}"
        image_path = COLLECTION_IMAGE_DIR / image_filename
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

    collection = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "image": image_filename,
    }
    data["collections"].append(collection)
    save_data(data)
    return collection


@app.get("/collection-image/{filename}")
async def get_collection_image(filename: str):
    image_path = COLLECTION_IMAGE_DIR / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), collection_id: Optional[str] = Form(None)):
    try:
        data = load_data()

        if collection_id and not any(c["id"] == collection_id for c in data["collections"]):
            raise HTTPException(status_code=404, detail="Collection not found")

        unique_id = uuid.uuid4().hex[:8]
        original_filename = file.filename
        stem = Path(original_filename).stem
        ext = Path(original_filename).suffix
        stored_filename = f"{stem}_{unique_id}{ext}"

        file_path = UPLOAD_DIR / stored_filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_entry = {
            "id": unique_id,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "collection_id": collection_id,
        }
        data["files"].append(file_entry)
        save_data(data)

        return file_entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/files")
def list_files(collection_id: Optional[str] = None):
    data = load_data()
    files = data["files"]
    if collection_id is not None:
        files = [f for f in files if f["collection_id"] == collection_id]
    return files


@app.get("/download/{stored_filename}")
async def download_file(stored_filename: str):
    file_path = UPLOAD_DIR / stored_filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    data = load_data()
    entry = next((f for f in data["files"] if f["stored_filename"] == stored_filename), None)
    download_name = entry["original_filename"] if entry else stored_filename

    return FileResponse(file_path, media_type="application/octet-stream", filename=download_name)


@app.put("/files/{file_id}")
async def update_file_content(file_id: str, file: UploadFile = File(...)):
    """Overwrite the stored bytes of a file (used to save edits)"""
    data = load_data()
    entry = next((f for f in data["files"] if f["id"] == file_id), None)

    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = UPLOAD_DIR / entry["stored_filename"]
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return entry


@app.delete("/files/{file_id}")
def delete_file(file_id: str):
    data = load_data()
    entry = next((f for f in data["files"] if f["id"] == file_id), None)

    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = UPLOAD_DIR / entry["stored_filename"]
    if file_path.exists():
        file_path.unlink()

    data["files"] = [f for f in data["files"] if f["id"] != file_id]
    save_data(data)
    return {"message": "File deleted successfully"}
