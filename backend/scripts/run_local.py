"""Windows-compatible local server launcher; production uses Procfile directly."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> None:
    import uvicorn

    config = uvicorn.Config(
        "guancha_api.main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")), loop="none"
    )
    server = uvicorn.Server(config)
    if sys.platform == "win32":
        # Psycopg async needs a selector loop on Windows. Scope this workaround
        # to the local launcher; Linux deployment keeps Uvicorn's normal loop.
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(server.serve())
        return
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
