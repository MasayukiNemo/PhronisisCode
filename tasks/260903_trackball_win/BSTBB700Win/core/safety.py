"""Phase2 safety helpers. Pure, no win32 calls. Mac-safe."""
from __future__ import annotations

MOUSEEVENTF_FROMTOUCH = 0xFF515700
_TOUCH_MASK = 0xFFFFFF00


def is_from_touch(extra_info: int) -> bool:
    """True when dwExtraInfo carries the touch signature.

    Upper-byte signature match (low byte ignored):
    (extra & 0xFFFFFF00) == 0xFF515700.
    """
    try:
        v = int(extra_info) & 0xFFFFFFFF
    except Exception:
        return False
    return (v & _TOUCH_MASK) == MOUSEEVENTF_FROMTOUCH


class EscTracker:
    """Fire once when Esc is hit `threshold` times within `window` seconds."""

    def __init__(self, window: float = 2.0, threshold: int = 5):
        self.window = float(window)
        self.threshold = int(threshold)
        self._times: list[float] = []

    def push(self, monotonic_now: float) -> bool:
        now = float(monotonic_now)
        lo = now - self.window
        self._times = [t for t in self._times if t >= lo]
        self._times.append(now)
        if len(self._times) >= self.threshold:
            self._times.clear()
            return True
        return False


def should_suppress_tilt(last: float | None, now: float, window: float = 0.3) -> bool:
    """True when a tilt arrived too soon after the previous one."""
    if last is None:
        return False
    try:
        return (float(now) - float(last)) < float(window)
    except Exception:
        return False
