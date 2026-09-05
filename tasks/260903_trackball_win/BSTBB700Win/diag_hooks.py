"""Hook startup diagnostics. Run with: python diag_hooks.py (Windows only)."""
from __future__ import annotations

import os
import sys


def main() -> int:
    print("diag_hooks: BSTBB700Win hook diagnostics")
    print(f"python={sys.version.split()[0]} frozen={bool(getattr(sys, 'frozen', False))}")
    if os.name != "nt":
        print("not Windows: hooks unavailable by design")
        return 0
    try:
        import ctypes
        from ctypes import wintypes
    except Exception as e:
        print(f"ctypes unavailable: {e}")
        return 1
    try:
        admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception as e:
        admin = f"unknown ({e})"
    print(f"admin={admin}")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.SetWindowsHookExW.restype = wintypes.HANDLE
    user32.SetWindowsHookExW.argtypes = (
        ctypes.c_int, ctypes.c_void_p, wintypes.HMODULE, wintypes.DWORD)
    user32.CallNextHookEx.restype = ctypes.c_long
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int,
                                  wintypes.WPARAM, wintypes.LPARAM)

    def _proc(nCode, wParam, lParam):
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    cb = HOOKPROC(_proc)  # keep ref during test
    # NOTE: hMod must be NULL. Passing a module handle fails with 126
    # because the ctypes thunk lives outside any module (see hooks.py).
    for name, hook_id in (("WH_KEYBOARD_LL", 13), ("WH_MOUSE_LL", 14)):
        try:
            ctypes.set_last_error(0)
        except Exception:
            pass
        try:
            h = user32.SetWindowsHookExW(hook_id, cb, None, 0)
        except Exception as e:
            print(f"{name}: exception {e!r}")
            continue
        try:
            err = ctypes.get_last_error()
        except Exception:
            err = "unknown"
        print(f"{name}: handle={h} last_error={err}")
        if h:
            try:
                user32.UnhookWindowsHookEx(h)
                print(f"{name}: unhooked ok")
            except Exception as e:
                print(f"{name}: unhook failed {e!r}")
    print("done: nonzero handle means install works; 0 means blocked (note last_error)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
