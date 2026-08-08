"""Explicit, one-call smoke test for the opt-in OpenAI screenshot provider.

This script is never imported by pytest. It reads its key only from the
environment and prints a redacted field summary, never the raw provider reply.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

# Allows the documented command to run from a source checkout without a
# global install. It is derived from this repository-relative script path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from guancha_api.infrastructure.storage.memory import InMemoryTemporaryPrivateStorage
from guancha_api.providers.openai import OpenAIResponsesProvider


async def run(image_path: Path) -> None:
    if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise SystemExit("Smoke input must be a local JPEG or PNG file.")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("GUANCHA_OPENAI_MODEL")
    if not api_key or not model:
        raise SystemExit("OPENAI_API_KEY and GUANCHA_OPENAI_MODEL must be set.")
    data = image_path.read_bytes()
    storage = InMemoryTemporaryPrivateStorage()
    object_key = f"smoke/{uuid4()}"
    content_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    await storage.put_private(object_key=object_key, content_type=content_type, data=data)
    provider = OpenAIResponsesProvider(api_key=api_key, model=model, storage=storage)
    try:
        result = await provider.extract(image_object_key=object_key)
    finally:
        await storage.delete(object_key=object_key)
    summary = {
        field: result.get(field)
        for field in ("product_name", "tea_category", "tea_subtype", "origin", "price", "risk_flags")
    }
    print({"result": summary, "evidence_count": len(result.get("evidence", []))})


def main() -> None:
    parser = argparse.ArgumentParser(description="One-call OpenAI screenshot extraction smoke test")
    parser.add_argument("image", type=Path, help="Path to a local JPEG or PNG screenshot")
    asyncio.run(run(parser.parse_args().image))


if __name__ == "__main__":
    main()
