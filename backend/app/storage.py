"""File storage behind a small interface (local disk now; S3 could implement it later)."""

import hashlib
import os
import uuid
from pathlib import Path
from typing import BinaryIO, Protocol

from app.errors import APIError

CHUNK_BYTES = 1024 * 1024


class StoredFile:
    def __init__(self, key: str, sha256: str, size: int) -> None:
        self.key = key
        self.sha256 = sha256
        self.size = size


class Storage(Protocol):
    def save_stream(self, stream: BinaryIO, suffix: str, max_bytes: int) -> StoredFile: ...
    def path_for(self, key: str) -> Path: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    """Streams uploads to disk while hashing, so large files never sit in memory.

    Writes to a temp name and renames at the end: readers never see a partial file.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_stream(self, stream: BinaryIO, suffix: str, max_bytes: int) -> StoredFile:
        key = f"{uuid.uuid4().hex}{suffix.lower()}"
        final = self.root / key
        tmp = self.root / f".{key}.part"
        digest = hashlib.sha256()
        size = 0
        try:
            with tmp.open("wb") as out:
                while chunk := stream.read(CHUNK_BYTES):
                    size += len(chunk)
                    if size > max_bytes:
                        raise APIError(
                            413, "file_too_large", f"Upload exceeds {max_bytes} bytes"
                        )
                    digest.update(chunk)
                    out.write(chunk)
            if size == 0:
                raise APIError(400, "empty_file", "Uploaded file is empty")
            os.replace(tmp, final)
        finally:
            tmp.unlink(missing_ok=True)
        return StoredFile(key=key, sha256=digest.hexdigest(), size=size)

    def path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise APIError(400, "bad_key", "Invalid storage key")
        return path

    def delete(self, key: str) -> None:
        self.path_for(key).unlink(missing_ok=True)


def get_storage() -> Storage:
    from app.config import get_settings

    return LocalStorage(get_settings().storage_dir)
