"""Low-level hook constants and pure decoders. Windows execution guarded."""
from __future__ import annotations

WH_MOUSE_LL = 14
WH_KEYBOARD_LL = 13

WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEHWHEEL = 0x020E
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

XBUTTON1 = 0x0001
XBUTTON2 = 0x0002


def hiword(v: int) -> int:
    u = int(v) & 0xFFFFFFFF
    h = (u >> 16) & 0xFFFF
    return h - 0x10000 if h >= 0x8000 else h


def decode_xbutton(mouse_data: int) -> int | None:
    hb = (int(mouse_data) >> 16) & 0xFFFF
    if hb == XBUTTON1:
        return 1
    if hb == XBUTTON2:
        return 2
    return None


def decode_tilt(mouse_data: int) -> int:
    return hiword(int(mouse_data))


def is_windows() -> bool:
    import os
    return os.name == "nt"


class HookEngine:
    """Skeleton. Real SetWindowsHookEx wiring runs only on Windows.

    on_mouse(button, is_down) -> 'precise' | 'emit' | 'passthrough'
    on_key(vk, is_down) -> bool consumed
    """

    def __init__(self, router=None):
        self.router = router
        self.running = False

    def start(self) -> bool:
        if not is_windows():
            return False
        # Real implementation lives here in Win env:
        # SetWindowsHookExW(WH_MOUSE_LL...), message pump, call router.
        self.running = True
        return True

    def stop(self) -> None:
        self.running = False
