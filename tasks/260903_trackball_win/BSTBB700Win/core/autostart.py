"""Auto-start via HKCU Run key. Mac-safe no-op (winreg lazily imported, no tkinter)."""
from __future__ import annotations

import os
import sys

APP_NAME = "BSTBB700Win"
RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def exe_path() -> str | None:
    if not is_frozen():
        return None
    try:
        exe = str(sys.executable)
        return exe or None
    except Exception:
        return None


def _is_windows() -> bool:
    return os.name == "nt"


def is_enabled() -> bool:
    if not is_frozen():
        return False
    if not _is_windows():
        return False
    try:
        import winreg
    except Exception:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_SUBKEY) as key:
            value, _kind = winreg.QueryValueEx(key, APP_NAME)
            return bool(str(value).strip())
    except Exception:
        return False


def set_enabled(on: bool) -> tuple[bool, str]:
    if not is_frozen():
        return (False, "開発実行中は登録不可（凍結exeのみ登録可）")
    if not _is_windows():
        return (False, "Windows以外では自動起動に未対応")
    try:
        import winreg
    except Exception as e:
        return (False, f"自動起動の変更に失敗: {e}")
    try:
        if on:
            exe = exe_path()
            if not exe:
                return (False, "実行パスを取得できない")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_SUBKEY,
                                0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
            return (True, "自動起動を登録した")
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_SUBKEY,
                                0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        return (True, "自動起動を解除した")
    except Exception as e:
        return (False, f"自動起動の変更に失敗: {e}")
