"""Phase2 tray icon. ctypes Shell_NotifyIconW, no tkinter. Mac import-safe.

All win32 access is function-local so import works on Mac.
Pure testable parts: menu IDs, precise_icon_id(), tooltip text.
"""
from __future__ import annotations

import os
import threading

MENU_SHOW_ID = 1001
MENU_TOGGLE_ID = 1002
MENU_QUIT_ID = 1003

IDI_APPLICATION = 32512
IDI_INFORMATION = 32516

WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
MF_STRING = 0x00000000
TPM_RIGHTBUTTON = 0x00000002
TPM_RETURNCMD = 0x00000100
WM_RBUTTONUP = 0x0205
WM_LBUTTONUP = 0x0202
WM_COMMAND = 0x0111
WM_DESTROY = 0x0002


def is_windows() -> bool:
    return os.name == "nt"


def precise_icon_id(active: bool) -> int:
    """System icon id: normal=IDI_APPLICATION, precise ON=IDI_INFORMATION."""
    return IDI_INFORMATION if active else IDI_APPLICATION


def precise_tooltip(active: bool) -> str:
    return "BSTBB700 精密ON" if active else "BSTBB700"


class TrayController:
    """Hidden-window tray icon on its own thread. Non-Windows: start()->False."""

    def __init__(self):
        self._on_show = None
        self._on_toggle = None
        self._on_quit = None
        self._wndproc = None
        self._nid = None
        self._hwnd = None
        self._thread = None
        self._running = False
        self._precise = False
        self.disabled = False
        self._lock = threading.Lock()

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._running

    def _set_running(self, v: bool) -> None:
        with self._lock:
            self._running = bool(v)

    def start(self, on_show=None, on_toggle_precise=None, on_quit=None) -> bool:
        if not is_windows():
            return False
        if self.is_active:
            return True
        # 保持参照 (GC防止)
        self._on_show = on_show
        self._on_toggle = on_toggle_precise
        self._on_quit = on_quit
        try:
            ok = self._start_windows()
        except Exception:
            self.disabled = True
            return False
        if not ok:
            self.disabled = True
            return False
        self.disabled = False
        return True

    def set_precise(self, active: bool) -> None:
        self._precise = bool(active)
        if not self.is_active:
            return
        try:
            self._modify_icon()
        except Exception:
            pass

    def stop(self) -> None:
        self._set_running(False)
        hwnd = self._hwnd
        if hwnd:
            try:
                from .winapi import user32
                user32.PostMessageW(int(hwnd), WM_DESTROY, 0, 0)
            except Exception:
                pass
        th = self._thread
        if th is not None:
            try:
                th.join(timeout=3)
            except Exception:
                pass
        self._thread = None
        self._hwnd = None
        self._nid = None
        self._wndproc = None
        self._on_show = None
        self._on_toggle = None
        self._on_quit = None

    # ---- Windows internals (typed winapi only) ----
    def _modify_icon(self) -> None:
        import ctypes
        from ctypes import wintypes
        from .winapi import icon_resource, shell32, user32
        if not self._hwnd or self._nid is None:
            return
        try:
            self._nid.hIcon = user32.LoadIconW(None, icon_resource(precise_icon_id(self._precise)))
            self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            tip = precise_tooltip(self._precise)
            self._nid.szTip = tip
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))
        except Exception:
            pass

    def _start_windows(self) -> bool:
        import ctypes
        from ctypes import wintypes
        from .winapi import WNDPROC, icon_resource, kernel32, shell32, user32
        ctrl = self
        ready = threading.Event()
        failure: list = []

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT),
                ("hIcon", wintypes.HANDLE),
                ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD),
                ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256),
                ("uVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64),
                ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", ctypes.c_byte * 16),
                ("hBalloonIcon", wintypes.HANDLE),
            ]

        def _call(cb):
            try:
                if cb is not None:
                    cb()
            except Exception:
                pass

        def wndproc(hwnd, msg, wparam, lparam):
            try:
                if msg == WM_TRAYICON:
                    lmsg = int(lparam) & 0xFFFF
                    if lmsg == WM_LBUTTONUP:
                        _call(ctrl._on_show)
                        return 0
                    if lmsg == WM_RBUTTONUP:
                        try:
                            hmenu = user32.CreatePopupMenu()
                            if hmenu:
                                precise = bool(ctrl._precise)
                                tlabel = ("精密 OFFに切替" if precise
                                          else "精密 ONに切替")
                                user32.AppendMenuW(hmenu, MF_STRING, MENU_SHOW_ID,
                                                   "設定を開く")
                                user32.AppendMenuW(hmenu, MF_STRING, MENU_TOGGLE_ID,
                                                   tlabel)
                                user32.AppendMenuW(hmenu, MF_STRING, MENU_QUIT_ID,
                                                   "終了")
                                pt = wintypes.POINT()
                                user32.GetCursorPos(ctypes.byref(pt))
                                user32.SetForegroundWindow(hwnd)
                                cmd = user32.TrackPopupMenu(
                                    hmenu, TPM_RIGHTBUTTON | TPM_RETURNCMD,
                                    pt.x, pt.y, 0, hwnd, None)
                                user32.DestroyMenu(hmenu)
                                if cmd == MENU_SHOW_ID:
                                    _call(ctrl._on_show)
                                elif cmd == MENU_TOGGLE_ID:
                                    _call(ctrl._on_toggle)
                                elif cmd == MENU_QUIT_ID:
                                    _call(ctrl._on_quit)
                        except Exception:
                            pass
                        return 0
                elif msg == WM_COMMAND:
                    cmd = int(wparam) & 0xFFFF
                    if cmd == MENU_SHOW_ID:
                        _call(ctrl._on_show)
                    elif cmd == MENU_TOGGLE_ID:
                        _call(ctrl._on_toggle)
                    elif cmd == MENU_QUIT_ID:
                        _call(ctrl._on_quit)
                    return 0
                elif msg == WM_DESTROY:
                    try:
                        if ctrl._nid is not None:
                            shell32.Shell_NotifyIconW(
                                NIM_DELETE, ctypes.byref(ctrl._nid))
                    except Exception:
                        pass
                    try:
                        user32.PostQuitMessage(0)
                    except Exception:
                        pass
                    return 0
            except Exception:
                pass
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc = WNDPROC(wndproc)  # GC防止の保持

        def pump():
            try:
                hinst = kernel32.GetModuleHandleW(None)

                class WNDCLASSW(ctypes.Structure):
                    _fields_ = [
                        ("style", wintypes.UINT),
                        ("lpfnWndProc", ctypes.c_void_p),
                        ("cbClsExtra", ctypes.c_int),
                        ("cbWndExtra", ctypes.c_int),
                        ("hInstance", wintypes.HANDLE),
                        ("hIcon", wintypes.HANDLE),
                        ("hCursor", wintypes.HANDLE),
                        ("hbrBackground", wintypes.HANDLE),
                        ("lpszMenuName", wintypes.LPCWSTR),
                        ("lpszClassName", wintypes.LPCWSTR),
                    ]

                cls = WNDCLASSW()
                cls.lpfnWndProc = ctypes.cast(self._wndproc,
                                              ctypes.c_void_p).value
                cls.hInstance = hinst
                cls.lpszClassName = "BSTBB700TrayHidden"
                if not user32.RegisterClassW(ctypes.byref(cls)):
                    # 既登録の可能性: 続行して Create を試みる
                    pass
                hwnd = user32.CreateWindowExW(
                    0, "BSTBB700TrayHidden", "BSTBB700Tray",
                    0, 0, 0, 0, 0, None, None, hinst, None)
                if not hwnd:
                    failure.append("CreateWindowEx failed")
                    ready.set()
                    return
                ctrl._hwnd = int(hwnd)
                nid = NOTIFYICONDATAW()
                nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
                nid.hWnd = hwnd
                nid.uID = 1
                nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
                nid.uCallbackMessage = WM_TRAYICON
                nid.hIcon = user32.LoadIconW(
                    None, icon_resource(precise_icon_id(bool(ctrl._precise))))
                nid.szTip = precise_tooltip(bool(ctrl._precise))
                if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
                    failure.append("Shell_NotifyIcon failed")
                    try:
                        user32.DestroyWindow(hwnd)
                    except Exception:
                        pass
                    ctrl._hwnd = None
                    ready.set()
                    return
                ctrl._nid = nid
                ctrl._set_running(True)
                ready.set()
                msg = wintypes.MSG()
                while True:
                    ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    if ret in (0, -1):
                        break
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            except Exception as e:
                failure.append(str(e))
                ready.set()
            finally:
                ctrl._set_running(False)

        self._thread = threading.Thread(target=pump, name="BSTBB700Tray",
                                        daemon=True)
        self._thread.start()
        ready.wait(timeout=10)
        if failure or not self.is_active:
            try:
                self.stop()
            except Exception:
                pass
            self.disabled = True
            return False
        return True
