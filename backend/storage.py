"""Google Cloud Storage helpers.

All file bytes live in a single private bucket (GCS_BUCKET). Nothing is ever
made public — bytes are only ever returned through authenticated endpoints.
"""
from google.cloud import storage as gcs

from config import GCS_BUCKET

_client = None


def _bucket():
    global _client
    if _client is None:
        _client = gcs.Client()
    return _client.bucket(GCS_BUCKET)


def upload_fileobj(blob_name: str, fileobj, content_type: str | None = None):
    blob = _bucket().blob(blob_name)
    blob.upload_from_file(fileobj, content_type=content_type)


def download_bytes(blob_name: str):
    blob = _bucket().blob(blob_name)
    if not blob.exists():
        return None
    return blob.download_as_bytes()


def delete_blob(blob_name: str):
    blob = _bucket().blob(blob_name)
    if blob.exists():
        blob.delete()
