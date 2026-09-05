"""Discovery log buffer."""
from __future__ import annotations

import os
import tempfile
import time
from collections import deque
from pathlib import Path


def default_debug_log_path() -> Path:
    base = os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
    return Path(base) / "bstbb700_debug.log"


class DiscoveryLog:
    def __init__(self, limit: int = 300):
        self._buf: deque[str] = deque(maxlen=limit)
        self._debug_file: str | None = None

    def set_debug_file(self, path) -> None:
        if path is None:
            self._debug_file = None
            return
        try:
            self._debug_file = str(path)
        except Exception:
            self._debug_file = None

    def add(self, line: str) -> None:
        self._buf.append(line)
        if self._debug_file:
            try:
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                with open(self._debug_file, "a", encoding="utf-8") as f:
                    f.write(f"{ts} {line}\n")
            except Exception:
                pass

    def clear(self) -> None:
        self._buf.clear()

    def lines(self) -> list[str]:
        return list(self._buf)

    def format_mouse(self, kind: str, detail: str) -> str:
        return f"mouse kind={kind} {detail}"

    def format_key(self, vk: int, down: bool) -> str:
        return f"key vk={vk} {'down' if down else 'up'}"
