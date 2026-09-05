"""Cursor magnifier: follows cursor upper-right while precise is active.

Capture is StretchBlt screen->window (no pixel conversion in Python).
All tkinter/Win32 touch happens on the UI thread via App's tick loop.
Pure geometry (testable): compute_layout().
"""
from __future__ import annotations

MAG_INTERVAL_MS = 100
OFFSET_X = 24
OFFSET_Y = 24
DEFAULT_SIZE = 320
MIN_SIZE = 200
MAX_SIZE = 480
ZOOM_CHOICES = (2, 3, 4)
DEFAULT_ZOOM = 2


def compute_layout(cx: float, cy: float, size: int, zoom: int,
                   screen_w: float, screen_h: float,
                   off_x: int = OFFSET_X, off_y: int = OFFSET_Y) -> dict:
    """Window rect (upper-right of cursor, clamped) + source rect (clamped)."""
    size = int(size)
    zoom = max(int(zoom), 1)
    wx = int(cx + off_x)
    wy = int(cy - off_y - size)
    wx = min(max(wx, 0), max(int(screen_w - size), 0))
    wy = min(max(wy, 0), max(int(screen_h - size), 0))
    src = max(size // zoom, 1)
    sx = int(cx - src // 2)
    sy = int(cy - src // 2)
    sx = min(max(sx, 0), max(int(screen_w - src), 0))
    sy = min(max(sy, 0), max(int(screen_h - src), 0))
    return {"wx": wx, "wy": wy, "size": size,
            "sx": sx, "sy": sy, "src": src}


class MagnifierController:
    """Owns the zoom Toplevel. UI thread only. Headless-safe no-op."""

    def __init__(self, settings_provider=None):
        self._get_settings = settings_provider or (lambda: None)
        self._win = None
        self.visible = False

    def _settings(self):
        try:
            return self._get_settings()
        except Exception:
            return None

    def _ensure_window(self, root) -> bool:
        if self._win is not None:
            try:
                if self._win.winfo_exists():
                    return True
            except Exception:
                pass
            self._win = None
        try:
            import tkinter as tk
        except Exception:
            return False
        try:
            win = tk.Toplevel(root)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.withdraw()
            self._win = win
            return True
        except Exception:
            return False

    def hide(self) -> None:
        self.visible = False
        win, self._win = self._win, None
        try:
            if win is not None:
                win.withdraw()
                win.destroy()
        except Exception:
            pass

    def tick(self, root, active: bool) -> bool:
        """Called from UI tick loop. Returns visibility. Never raises."""
        try:
            s = self._settings()
            enabled = bool(getattr(s, "magnifier_enabled", False)) if s else False
            if not (active and enabled and root is not None):
                if self.visible or self._win is not None:
                    self.hide()
                return False
            size = int(getattr(s, "magnifier_size", DEFAULT_SIZE) or DEFAULT_SIZE)
            size = min(max(size, MIN_SIZE), MAX_SIZE)
            zoom = int(getattr(s, "magnifier_zoom", DEFAULT_ZOOM) or DEFAULT_ZOOM)
            if not self._ensure_window(root):
                return False
            try:
                sw = float(root.winfo_screenwidth())
                sh = float(root.winfo_screenheight())
            except Exception:
                return self.visible
            cx, cy = self._cursor_pos()
            lay = compute_layout(cx, cy, size, zoom, sw, sh)
            try:
                self._win.geometry(f"{lay['size']}x{lay['size']}+{lay['wx']}+{lay['wy']}")
                self._win.deiconify()
                self._win.lift()
            except Exception:
                return self.visible
            self._paint(lay)
            self.visible = True
            return True
        except Exception:
            return False

    def _cursor_pos(self) -> tuple:
        try:
            from .winapi import user32
        except ImportError:
            from core.winapi import user32
        try:
            import ctypes
            from ctypes import wintypes

            class _PT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

            pt = _PT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                return (float(pt.x), float(pt.y))
        except Exception:
            pass
        return (0.0, 0.0)

    def _paint(self, lay: dict) -> None:
        try:
            from .winapi import SRCCOPY, gdi32, user32
        except ImportError:
            from core.winapi import SRCCOPY, gdi32, user32
        try:
            hwnd = int(self._win.winfo_id())
        except Exception:
            return
        try:
            h_screen = user32.GetDC(None)
            h_win = user32.GetDC(hwnd)
            try:
                gdi32.StretchBlt(h_win, 0, 0, lay["size"], lay["size"],
                                 h_screen, lay["sx"], lay["sy"],
                                 lay["src"], lay["src"], SRCCOPY)
            finally:
                try:
                    user32.ReleaseDC(hwnd, h_win)
                except Exception:
                    pass
                try:
                    user32.ReleaseDC(None, h_screen)
                except Exception:
                    pass
        except Exception:
            pass
