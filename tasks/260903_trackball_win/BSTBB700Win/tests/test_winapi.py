"""winapi typing regression + direct proc-call tests. Mac-safe (skip live parts)."""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import core.winapi as winapi

_USER32_FNS = [
    "SetWindowsHookExW", "CallNextHookEx", "UnhookWindowsHookEx",
    "PostThreadMessageW", "SendInput", "MapVirtualKeyW", "GetKeyState",
    "SystemParametersInfoW", "CreateWindowExW", "DefWindowProcW",
    "TrackPopupMenu", "LoadIconW", "RegisterClassW", "GetMessageW",
]
_SHELL32_FNS = ["Shell_NotifyIconW"]


def test_winapi_import_safe():
    assert winapi.IS_WINDOWS == (os.name == "nt")


def test_winapi_prototypes_typed():
    if os.name != "nt":
        assert winapi.user32 is None
        assert winapi.HOOKPROC is None
        return
    assert winapi.HOOKPROC is not None
    for name in _USER32_FNS:
        fn = getattr(winapi.user32, name)
        assert fn.argtypes is not None, name
        assert fn.restype is not None, name
    for name in _SHELL32_FNS:
        fn = getattr(winapi.shell32, name)
        assert fn.argtypes is not None, name
        assert fn.restype is not None, name


def test_proc_direct_call_passthrough():
    """Synchronously drive the real procs with fabricated structs (no system effect)."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    from core.hooks import HookEngine

    seen = []
    eng = HookEngine(router=lambda b, d: seen.append((b, d)) or "passthrough",
                     key_router=lambda vk, down: False)
    assert eng.start() is True
    try:
        class MS(ctypes.Structure):
            _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD),
                        ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.c_void_p)]

        buf = MS()
        addr = ctypes.addressof(buf)
        r = eng._mouse_proc(0, 0x0200, addr)  # WM_MOUSEMOVE passthrough
        assert isinstance(int(r), int)

        class KS(ctypes.Structure):
            _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                        ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.c_void_p)]

        kbuf = KS()
        kbuf.vkCode = 65
        r2 = eng._kbd_proc(0, 0x0100, ctypes.addressof(kbuf))  # A down
        assert isinstance(int(r2), int)
    finally:
        eng.stop()
    assert eng.running is False
