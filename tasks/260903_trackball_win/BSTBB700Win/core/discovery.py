"""Discovery log buffer."""
from __future__ import annotations

from collections import deque


class DiscoveryLog:
    def __init__(self, limit: int = 300):
        self._buf: deque[str] = deque(maxlen=limit)

    def add(self, line: str) -> None:
        self._buf.append(line)

    def clear(self) -> None:
        self._buf.clear()

    def lines(self) -> list[str]:
        return list(self._buf)

    def format_mouse(self, kind: str, detail: str) -> str:
        return f"mouse kind={kind} {detail}"

    def format_key(self, vk: int, down: bool) -> str:
        return f"key vk={vk} {'down' if down else 'up'}"
