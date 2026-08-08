"""Stable request fingerprints for persisted idempotency records."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


def request_hash(payload: Any) -> str:
    """Hash canonical client input only; callers must exclude IDs and timestamps."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(encoded.encode("utf-8")).hexdigest()
