"""Firestore-backed metadata store (the persistent source of truth).

Replaces the old ephemeral data.json. Two collections:
  - "collections": {id, name, image, created_by}
  - "files":       {id, original_filename, stored_filename, gcs_path,
                    content_type, collection_id, owner}
"""
import firebase_app  # noqa: F401  (ensures Firebase Admin is initialized)

from firebase_admin import firestore

_db = None


def _client():
    global _db
    if _db is None:
        _db = firestore.client()
    return _db


# --- collections ---------------------------------------------------------

def list_collections():
    return [doc.to_dict() for doc in _client().collection("collections").stream()]


def get_collection(collection_id: str):
    doc = _client().collection("collections").document(collection_id).get()
    return doc.to_dict() if doc.exists else None


def add_collection(data: dict):
    _client().collection("collections").document(data["id"]).set(data)


# --- files ---------------------------------------------------------------

def list_files(collection_id=None):
    query = _client().collection("files")
    if collection_id is not None:
        query = query.where("collection_id", "==", collection_id)
    return [doc.to_dict() for doc in query.stream()]


def get_file(file_id: str):
    doc = _client().collection("files").document(file_id).get()
    return doc.to_dict() if doc.exists else None


def add_file(data: dict):
    _client().collection("files").document(data["id"]).set(data)


def delete_file(file_id: str):
    _client().collection("files").document(file_id).delete()
