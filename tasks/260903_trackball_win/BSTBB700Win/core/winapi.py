"""Typed Win32 prototypes (64-bit safe). All ctypes API calls go through here.

Background: calling Win32 without argtypes makes ctypes treat every Python
int as c_int, truncating 64-bit handles/pointers (lParam, HWND, HHOOK, ...).
That corrupted the low-level hook chain and froze all input. Never call
ctypes.windll.* directly; use the handles below.
Mac-safe: import never raises; all handles are None off Windows.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

IS_WINDOWS = os.name == "nt"

SRCCOPY = 0x00CC0020

if IS_WINDOWS:
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    try:
        _shcore = ctypes.WinDLL("shcore", use_last_error=True)
    except Exception:
        _shcore = None

    HOOKPROC = ctypes.WINFUNCTYPE(
        ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_long, wintypes.HWND, wintypes.UINT,
        wintypes.WPARAM, wintypes.LPARAM)

    # ---- hooks ----
    _user32.SetWindowsHookExW.argtypes = (
        ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
    _user32.SetWindowsHookExW.restype = wintypes.HANDLE
    _user32.CallNextHookEx.argtypes = (
        wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    _user32.CallNextHookEx.restype = ctypes.c_long
    _user32.UnhookWindowsHookEx.argtypes = (wintypes.HANDLE,)
    _user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    _user32.PostThreadMessageW.argtypes = (
        wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    _user32.PostThreadMessageW.restype = wintypes.BOOL
    _kernel32.GetCurrentThreadId.argtypes = ()
    _kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    _kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
    _kernel32.GetModuleHandleW.restype = wintypes.HMODULE

    # ---- keyboard/mouse ----
    _user32.SendInput.argtypes = (wintypes.UINT, ctypes.c_void_p, ctypes.c_int)
    _user32.SendInput.restype = wintypes.UINT
    _user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
    _user32.MapVirtualKeyW.restype = wintypes.UINT
    _user32.GetKeyState.argtypes = (ctypes.c_int,)
    _user32.GetKeyState.restype = wintypes.SHORT
    _user32.SystemParametersInfoW.argtypes = (
        wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT)
    _user32.SystemParametersInfoW.restype = wintypes.BOOL

    # ---- tray window ----
    _user32.RegisterClassW.argtypes = (ctypes.c_void_p,)
    _user32.RegisterClassW.restype = wintypes.ATOM
    _user32.CreateWindowExW.argtypes = (
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID)
    _user32.CreateWindowExW.restype = wintypes.HWND
    _user32.DestroyWindow.argtypes = (wintypes.HWND,)
    _user32.DestroyWindow.restype = wintypes.BOOL
    _user32.DefWindowProcW.argtypes = (
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    _user32.DefWindowProcW.restype = ctypes.c_long
    _user32.CreatePopupMenu.argtypes = ()
    _user32.CreatePopupMenu.restype = wintypes.HMENU
    _user32.AppendMenuW.argtypes = (
        wintypes.HMENU, wintypes.UINT, ctypes.c_void_p, wintypes.LPCWSTR)
    _user32.AppendMenuW.restype = wintypes.BOOL
    _user32.GetCursorPos.argtypes = (ctypes.c_void_p,)
    _user32.GetCursorPos.restype = wintypes.BOOL
    _user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    _user32.SetForegroundWindow.restype = wintypes.BOOL
    _user32.TrackPopupMenu.argtypes = (
        wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, wintypes.HWND, wintypes.LPVOID)
    _user32.TrackPopupMenu.restype = wintypes.UINT
    _user32.DestroyMenu.argtypes = (wintypes.HMENU,)
    _user32.DestroyMenu.restype = wintypes.BOOL
    _user32.PostQuitMessage.argtypes = (ctypes.c_int,)
    _user32.PostQuitMessage.restype = None
    _user32.GetMessageW.argtypes = (
        ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT)
    _user32.GetMessageW.restype = ctypes.c_int
    _user32.TranslateMessage.argtypes = (ctypes.c_void_p,)
    _user32.TranslateMessage.restype = wintypes.BOOL
    _user32.DispatchMessageW.argtypes = (ctypes.c_void_p,)
    _user32.DispatchMessageW.restype = ctypes.c_long
    _user32.PostMessageW.argtypes = (
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    _user32.PostMessageW.restype = wintypes.BOOL
    _user32.LoadIconW.argtypes = (wintypes.HINSTANCE, wintypes.LPCWSTR)
    _user32.LoadIconW.restype = wintypes.HANDLE
    _shell32.Shell_NotifyIconW.argtypes = (wintypes.DWORD, ctypes.c_void_p)
    _shell32.Shell_NotifyIconW.restype = wintypes.BOOL

    _user32.SetProcessDPIAware.argtypes = ()
    _user32.SetProcessDPIAware.restype = wintypes.BOOL
    if _shcore is not None:
        try:
            _shcore.SetProcessDpiAwareness.argtypes = (ctypes.c_int,)
            _shcore.SetProcessDpiAwareness.restype = ctypes.c_int
        except Exception:
            pass

    user32 = _user32
    kernel32 = _kernel32
    shell32 = _shell32
    shcore = _shcore
else:
    HOOKPROC = None  # type: ignore[assignment]
    WNDPROC = None  # type: ignore[assignment]
    user32 = None  # type: ignore[assignment]
    kernel32 = None  # type: ignore[assignment]
    shell32 = None  # type: ignore[assignment]
    shcore = None  # type: ignore[assignment]


def enable_dpi_awareness() -> str:
    """プロセスをDPI対応にする。Tk生成より先に呼ぶ。戻り値は方式名。"""
    if not IS_WINDOWS:
        return "non-windows"
    try:
        if shcore is not None:
            if int(shcore.SetProcessDpiAwareness(2)) == 0:  # PER_MONITOR_AWARE
                return "per-monitor"
    except Exception:
        pass
    try:
        if user32 is not None and bool(user32.SetProcessDPIAware()):
            return "system"
    except Exception:
        pass
    return "unaware"


def last_error() -> int | str:
    try:
        return int(ctypes.get_last_error())
    except Exception:
        return "unknown"


def icon_resource(icon_id: int):
    """MAKEINTRESOURCE equivalent for LoadIconW etc. (None off Windows)."""
    if not IS_WINDOWS:
        return None
    return ctypes.cast(icon_id, wintypes.LPCWSTR)
