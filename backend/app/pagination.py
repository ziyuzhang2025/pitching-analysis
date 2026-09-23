"""Cursor pagination over ascending integer ids.

A cursor is an opaque base64 token wrapping the last id of the previous page, so
clients never do offset arithmetic and pages stay stable while rows are added.
"""

import base64
import json
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.errors import APIError

T = TypeVar("T")
MAX_LIMIT = 100


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None


def encode_cursor(last_id: int) -> str:
    raw = json.dumps({"after": last_id}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode()))["after"]
        if not isinstance(value, int) or value < 0:
            raise ValueError
        return value
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise APIError(400, "bad_cursor", "Invalid pagination cursor") from exc


def clamp_limit(limit: int) -> int:
    if limit < 1:
        raise APIError(400, "bad_limit", "limit must be >= 1")
    return min(limit, MAX_LIMIT)


def next_cursor_for(rows: list, limit: int) -> str | None:
    """Pass rows fetched with LIMIT limit+1; returns the cursor if a next page exists."""
    if len(rows) > limit:
        return encode_cursor(rows[limit - 1].id)
    return None
