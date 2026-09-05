"""Phase2 HUD pill. tkinter only, no ctypes/winreg. Mac import-safe."""
from __future__ import annotations

try:
    import tkinter as tk
except Exception:  # headless import safety
    tk = None  # type: ignore

HIDE_MS = 1500


class HudController:
    """Top-right pill showing precise state. Thread-safe flash via root.after(0)."""

    def __init__(self):
        self._root = None
        self._win = None
        self._label = None
        self._timer = None

    def attach(self, root) -> None:
        self._root = root

    def _text(self, active: bool, scale: float) -> str:
        try:
            pct = int(round(float(scale) * 100))
        except Exception:
            pct = 25
        return f"精密 ON {pct}%" if active else f"精密 OFF {pct}%"

    def flash(self, active: bool, scale: float) -> None:
        root = self._root
        if root is None:
            return
        try:
            after = getattr(root, "after", None)
            if after is None:
                return
            after(0, lambda: self._show(bool(active), float(scale)))
        except Exception:
            pass

    def _show(self, active: bool, scale: float) -> None:
        if tk is None:
            return
        root = self._root
        if root is None:
            return
        try:
            win = self._win
            if win is not None:
                try:
                    if not win.winfo_exists():
                        win = None
                        self._win = None
                        self._label = None
                except Exception:
                    win = None
                    self._win = None
                    self._label = None
            text = self._text(active, scale)
            bg = "#1a7f37" if active else "#6e6e6e"
            if win is not None and self._label is not None:
                # 合体仕様: 表示中は文言更新のみ、タイマー追加なし
                try:
                    self._label.config(text=text, background=bg)
                    win.config(background=bg)
                except Exception:
                    pass
                return
            w = tk.Toplevel(root)
            try:
                w.overrideredirect(True)
            except Exception:
                pass
            try:
                w.attributes("-topmost", True)
            except Exception:
                pass
            try:
                w.config(background=bg)
                sw = int(root.winfo_screenwidth())
                w.geometry(f"+{max(sw - 240, 0)}+24")
            except Exception:
                pass
            try:
                lab = tk.Label(w, text=text, background=bg, foreground="white",
                               font=("TkDefaultFont", 11, "bold"), padx=12, pady=6)
                lab.pack()
            except Exception:
                try:
                    w.destroy()
                except Exception:
                    pass
                self._win = None
                self._label = None
                return
            self._win = w
            self._label = lab
            try:
                self._timer = root.after(HIDE_MS, self._hide_direct)
            except Exception:
                self._timer = None
        except Exception:
            pass

    def _hide_direct(self) -> None:
        root = self._root
        if root is not None and self._timer is not None:
            try:
                root.after_cancel(self._timer)
            except Exception:
                pass
        self._timer = None
        win, self._win = self._win, None
        self._label = None
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass

    def hide(self) -> None:
        root = self._root
        if root is None:
            self._timer = None
            self._win = None
            self._label = None
            return
        try:
            after = getattr(root, "after", None)
            if after is None:
                self._hide_direct()
                return
            after(0, self._hide_direct)
        except Exception:
            pass
