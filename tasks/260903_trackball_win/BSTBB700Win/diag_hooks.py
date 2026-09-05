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
        from core.winapi import HOOKPROC, last_error, user32
    except ImportError:
        from winapi import HOOKPROC, last_error, user32
    try:
        import ctypes
        admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception as e:
        admin = f"unknown ({e})"
    print(f"admin={admin}")

    def _proc(nCode, wParam, lParam):
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    cb = HOOKPROC(_proc)  # keep ref during test
    # NOTE: hMod must be NULL. Passing a module handle fails with 126
    # because the ctypes thunk lives outside any module (see hooks.py).
    for name, hook_id in (("WH_KEYBOARD_LL", 13), ("WH_MOUSE_LL", 14)):
        try:
            h = user32.SetWindowsHookExW(hook_id, cb, None, 0)
        except Exception as e:
            print(f"{name}: exception {e!r}")
            continue
        print(f"{name}: handle={h} last_error={last_error()}")
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
