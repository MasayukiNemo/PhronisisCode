"""Cursor magnifier: follows cursor upper-right while precise is active.

Capture is StretchBlt screen->window (no pixel conversion in Python).
All tkinter/Win32 touch happens on the UI thread via App's tick loop.
Pure geometry (testable): compute_layout().
"""
from __future__ import annotations

MAG_INTERVAL_MS = 100
OFFSET_X = 24
OFFSET_Y = 24
DEFAULT_SIZE = 160
MIN_SIZE = 80
MAX_SIZE = 480
ZOOM_CHOICES = (2, 3, 4)
DEFAULT_ZOOM = 2


def geometry_string(size: int, wx: int, wy: int) -> str:
    """符号つき形状文字列。負座標（左・上画面）でも壊れない。"""
    return f"{int(size)}x{int(size)}{int(wx):+d}{int(wy):+d}"


def virtual_screen() -> tuple:
    """(ox, oy, w, h)。失敗時はプライマリ相当に縮退。"""
    try:
        from .winapi import (SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN,
                             SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, user32)
    except ImportError:
        from core.winapi import (SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN,
                                 SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, user32)
    try:
        ox = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
        oy = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        w = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
        h = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
        if w > 0 and h > 0:
            return (ox, oy, w, h)
    except Exception:
        pass
    return (0, 0, 0, 0)


def compute_layout(cx: float, cy: float, size: int, zoom: int,
                   screen_w: float, screen_h: float,
                   off_x: int = OFFSET_X, off_y: int = OFFSET_Y,
                   org_x: float = 0.0, org_y: float = 0.0) -> dict:
    """Window rect (upper-right of cursor, clamped) + source rect (clamped).

    screen_w/h と org_x/y は仮想画面全体で渡す（マルチ画面対応）。
    """
    size = int(size)
    zoom = max(int(zoom), 1)
    x0, y0 = float(org_x), float(org_y)
    x1, y1 = x0 + float(screen_w), y0 + float(screen_h)
    wx = int(cx + off_x)
    wy = int(cy - off_y - size)
    wx = min(max(wx, int(x0)), max(int(x1 - size), int(x0)))
    wy = min(max(wy, int(y0)), max(int(y1 - size), int(y0)))
    src = max(size // zoom, 1)
    sx = int(cx - src // 2)
    sy = int(cy - src // 2)
    sx = min(max(sx, int(x0)), max(int(x1 - src), int(x0)))
    sy = min(max(sy, int(y0)), max(int(y1 - src), int(y0)))
    return {"wx": wx, "wy": wy, "size": size,
            "sx": sx, "sy": sy, "src": src}


class MagnifierController:
    """Owns the zoom Toplevel. UI thread only. Headless-safe no-op."""

    def __init__(self, settings_provider=None):
        self._get_settings = settings_provider or (lambda: None)
        self._win = None
        self.visible = False
        self._region_size: int | None = None
        self.region_applied = False
        self.last_paint_ok: bool | None = None
        self.last_paint_error: int | str | None = None
        self.last_layout: dict | None = None

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
        self._region_size = None
        self.region_applied = False
        win, self._win = self._win, None
        try:
            if win is not None:
                win.withdraw()
                win.destroy()
        except Exception:
            pass

    def status_text(self) -> str:
        if not self.visible:
            return "拡大鏡: 停止中"
        paint = "描画OK" if self.last_paint_ok else f"描画NG({self.last_paint_error})"
        shape = "円形" if self.region_applied else "矩形"
        lay = self.last_layout or {}
        return (f"拡大鏡: 表示中・{paint}・{shape} "
                f"窓({lay.get('wx')},{lay.get('wy')},{lay.get('size')}) "
                f"元({lay.get('sx')},{lay.get('sy')},{lay.get('src')})")

    def _apply_circle(self, size: int) -> None:
        """窓を円形にする。大きさ変化時のみ適用。失敗時は矩形のまま。
        リージョン所有権はSetWindowRgn成功でOSへ移るためDeleteしない。
        窓破棄時にOSが回収する。"""
        if self._region_size == int(size):
            return
        self.region_applied = False
        try:
            from .winapi import gdi32, user32
        except ImportError:
            from core.winapi import gdi32, user32
        try:
            hwnd = int(self._win.winfo_id())
            hrgn = gdi32.CreateEllipticRgn(0, 0, int(size) + 1, int(size) + 1)
            if not hrgn:
                return
            if int(user32.SetWindowRgn(hwnd, hrgn, True)):
                self._region_size = int(size)
                self.region_applied = True
                return
            try:
                gdi32.DeleteObject(hrgn)
            except Exception:
                pass
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
            ox, oy, vw, vh = virtual_screen()
            if vw <= 0 or vh <= 0:
                # 縮退: プライマリ画面。それも取れなければ現状維持。
                # DPI・配置は毎tick再取得のため実行中切替にも追従する。
                try:
                    vw = float(root.winfo_screenwidth())
                    vh = float(root.winfo_screenheight())
                except Exception:
                    return self.visible
            cx, cy = self._cursor_pos()
            lay = compute_layout(cx, cy, size, zoom, vw, vh, org_x=ox, org_y=oy)
            self.last_layout = dict(lay)
            try:
                self._win.geometry(geometry_string(lay["size"], lay["wx"], lay["wy"]))
                self._win.deiconify()
                self._win.lift()
            except Exception:
                return self.visible
            self._apply_circle(lay["size"])
            self.last_paint_ok = self._paint(lay)
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

    def _paint(self, lay: dict) -> bool:
        try:
            from .winapi import SRCCOPY, gdi32, last_error, user32
        except ImportError:
            from core.winapi import SRCCOPY, gdi32, last_error, user32
        try:
            hwnd = int(self._win.winfo_id())
        except Exception:
            self.last_paint_error = "no-hwnd"
            return False
        try:
            h_screen = user32.GetDC(None)
            h_win = user32.GetDC(hwnd)
            try:
                ok = bool(gdi32.StretchBlt(h_win, 0, 0, lay["size"], lay["size"],
                                           h_screen, lay["sx"], lay["sy"],
                                           lay["src"], lay["src"], SRCCOPY))
                self.last_paint_error = None if ok else last_error()
            finally:
                try:
                    user32.ReleaseDC(hwnd, h_win)
                except Exception:
                    pass
                try:
                    user32.ReleaseDC(None, h_screen)
                except Exception:
                    pass
            return ok
        except Exception as e:
            self.last_paint_error = str(e)
            return False
