"""Low-level hook constants, pure decoders, and Windows hook engine.

Pure decoders (hiword/decode_xbutton/decode_tilt) are platform independent
and covered by tests. HookEngine wiring runs only on Windows; on other
platforms start() returns False so Mac-side logic tests stay green.
"""
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

LLMHF_INJECTED = 0x00000001
LLMHF_LOWER_IL_INJECTED = 0x00000002
LLKHF_INJECTED = 0x00000010

HC_ACTION = 0


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


def is_injected_mouse(flags: int) -> bool:
    return bool(int(flags) & (LLMHF_INJECTED | LLMHF_LOWER_IL_INJECTED))


def is_injected_key(flags: int) -> bool:
    return bool(int(flags) & LLKHF_INJECTED)


class HookEngine:
    """WH_MOUSE_LL + WH_KEYBOARD_LL engine.

    router(button, is_down) -> 'precise' | 'emit' | 'passthrough'
    key_router(vk, is_down) -> True when consumed (swallow)
    discovery: DiscoveryLog-like with .add(str)
    swap_provider() -> bool, tilt_provider() -> bool
    """

    def __init__(self, router=None, key_router=None, discovery=None,
                 swap_provider=None, tilt_provider=None, touch_filter=None):
        self.router = router
        self.key_router = key_router
        self.discovery = discovery
        self.swap_provider = swap_provider
        self.tilt_provider = tilt_provider
        self.touch_filter = touch_filter
        self.running = False
        self._thread = None
        self._thread_id = None
        self._mouse_hook = None
        self._kbd_hook = None
        self._mouse_proc = None
        self._kbd_proc = None
        self.last_error: str | None = None

    def _log(self, line: str) -> None:
        try:
            if self.discovery is not None:
                self.discovery.add(line)
        except Exception:
            pass

    def _swap(self) -> bool:
        try:
            return bool(self.swap_provider()) if self.swap_provider else False
        except Exception:
            return False

    def _tilt_inv(self) -> bool:
        try:
            return bool(self.tilt_provider()) if self.tilt_provider else False
        except Exception:
            return False

    def should_skip_touch(self, extra_info: int) -> bool:
        """Pure helper: True when HWHEEL event is touch-derived (passthrough)."""
        try:
            if self.touch_filter is None:
                return False
            return bool(self.touch_filter(int(extra_info)))
        except Exception:
            return False

    # Pure routing helpers (testable without Windows)
    def resolve_mouse_event(self, msg: int, mouse_data: int) -> tuple | None:
        """Return (button, is_down) or None when not ours. No side effects."""
        from .mapper import resolve_mbutton, resolve_tilt, resolve_xbutton
        if msg in (WM_XBUTTONDOWN, WM_XBUTTONUP):
            xid = decode_xbutton(mouse_data)
            if xid is None:
                return None
            button = resolve_xbutton(xid, swap_back_forward=self._swap())
            if button is None:
                return None
            return (button, msg == WM_XBUTTONDOWN)
        if msg in (WM_MBUTTONDOWN, WM_MBUTTONUP):
            return (resolve_mbutton(), msg == WM_MBUTTONDOWN)
        if msg == WM_MOUSEHWHEEL:
            button = resolve_tilt(decode_tilt(mouse_data), tilt_inverted=self._tilt_inv())
            if button is None:
                return None
            return (button, True)  # HWHEEL has no up event; pulse as down
        return None

    def start(self) -> bool:
        if self.running:
            return True
        if not is_windows():
            return False
        try:
            import ctypes
            import threading
            from ctypes import wintypes
        except Exception as e:
            self.last_error = f"ctypes unavailable: {e}"
            return False
        try:
            return self._start_windows(ctypes, threading, wintypes)
        except Exception as e:
            self.last_error = str(e)
            return False

    def _start_windows(self, ctypes, threading, wintypes) -> bool:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD),
                        ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.c_void_p)]

        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                        ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.c_void_p)]

        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int,
                                      wintypes.WPARAM, wintypes.LPARAM)

        engine = self

        def mouse_proc(nCode, wParam, lParam):
            if nCode == HC_ACTION:
                try:
                    msg = int(wParam)
                    info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    if is_injected_mouse(info.flags):
                        return user32.CallNextHookEx(None, nCode, wParam, lParam)
                    if int(msg) == WM_MOUSEHWHEEL:
                        try:
                            raw = info.dwExtraInfo
                            extra = int(raw) if isinstance(raw, int) else int(
                                getattr(raw, "value", 0) or 0)
                        except Exception:
                            extra = 0
                        if engine.should_skip_touch(extra):
                            return user32.CallNextHookEx(None, nCode, wParam, lParam)
                    resolved = engine.resolve_mouse_event(msg, int(info.mouseData))
                    if resolved is not None:
                        button, is_down = resolved
                        engine._log(f"mouse kind={button} {'down' if is_down else 'up'}")
                        action = "passthrough"
                        if engine.router is not None:
                            try:
                                action = engine.router(button, is_down) or "passthrough"
                            except Exception:
                                action = "passthrough"
                        if action in ("emit", "precise"):
                            return 1  # swallow
                except Exception:
                    pass
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        def kbd_proc(nCode, wParam, lParam):
            if nCode == HC_ACTION:
                try:
                    msg = int(wParam)
                    info = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    if is_injected_key(info.flags):
                        return user32.CallNextHookEx(None, nCode, wParam, lParam)
                    vk = int(info.vkCode)
                    is_down = msg in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    is_up = msg in (WM_KEYUP, WM_SYSKEYUP)
                    if (is_down or is_up) and engine.key_router is not None:
                        try:
                            consumed = engine.key_router(vk, is_down)
                        except Exception:
                            consumed = False
                        if consumed:
                            engine._log(f"key vk={vk} {'down' if is_down else 'up'} consumed")
                            return 1
                except Exception:
                    pass
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        self._mouse_proc = HOOKPROC(mouse_proc)
        self._kbd_proc = HOOKPROC(kbd_proc)

        started = threading.Event()
        failure: list = []

        def pump():
            h_mouse = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_proc,
                                               kernel32.GetModuleHandleW(None), 0)
            h_kbd = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kbd_proc,
                                             kernel32.GetModuleHandleW(None), 0)
            if not h_mouse or not h_kbd:
                if h_mouse:
                    user32.UnhookWindowsHookEx(h_mouse)
                if h_kbd:
                    user32.UnhookWindowsHookEx(h_kbd)
                failure.append(f"SetWindowsHookEx failed mouse={h_mouse} kbd={h_kbd}")
                started.set()
                return
            self._mouse_hook = h_mouse
            self._kbd_hook = h_kbd
            self._thread_id = kernel32.GetCurrentThreadId()
            started.set()
            msg = wintypes.MSG()
            while True:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret in (0, -1):
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        self._thread = threading.Thread(target=pump, name="BSTBB700Hooks", daemon=True)
        self._thread.start()
        started.wait(timeout=10)
        if failure or not self._mouse_hook or not self._kbd_hook:
            self.last_error = failure[0] if failure else "hook install failed"
            self._mouse_hook = None
            self._kbd_hook = None
            return False
        self.running = True
        return True

    def stop(self) -> None:
        if not self.running and not self._mouse_hook and not self._kbd_hook:
            self.running = False
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            if self._mouse_hook:
                try:
                    user32.UnhookWindowsHookEx(self._mouse_hook)
                except Exception:
                    pass
            if self._kbd_hook:
                try:
                    user32.UnhookWindowsHookEx(self._kbd_hook)
                except Exception:
                    pass
            try:
                if self._thread_id:
                    user32.PostThreadMessageW(int(self._thread_id), 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass
        except Exception:
            pass
        finally:
            self._mouse_hook = None
            self._kbd_hook = None
            self._thread_id = None
            self.running = False
