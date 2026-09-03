"""BSTBB700Win tkinter settings UI. Runs on Windows, importable on Mac for syntax check.

Entry points (both work):
  cd BSTBB700Win & python app.py
  cd <parent> & python -m BSTBB700Win.app
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.discovery import DiscoveryLog
    from core.hooks import HookEngine
    from core.keys import emit
    from core.mapper import decide_action
    from core.precise import PreciseController, WinSpeedBackend, is_hold_capable_trigger
    from core.settings import (
        TRIGGER_VK,
        ButtonID,
        KeyCombo,
        PreciseMode,
        PreciseTrigger,
        SettingsStore,
    )
except ImportError:  # `python -m BSTBB700Win.app` package mode
    from .core.discovery import DiscoveryLog
    from .core.hooks import HookEngine
    from .core.keys import emit
    from .core.mapper import decide_action
    from .core.precise import PreciseController, WinSpeedBackend, is_hold_capable_trigger
    from .core.settings import (
        TRIGGER_VK,
        ButtonID,
        KeyCombo,
        PreciseMode,
        PreciseTrigger,
        SettingsStore,
    )

import tkinter as tk
from tkinter import ttk


BUTTON_ROWS = [
    ("back", "戻る (XBUTTON1)"),
    ("forward", "進む (XBUTTON2)"),
    ("center", "中央押し (MBUTTON)"),
    ("tiltLeft", "チルト左 (HWHEEL-)"),
    ("tiltRight", "チルト右 (HWHEEL+)"),
]

TRIGGER_CHOICES = [
    "f13", "f14", "f15", "capsLock", "customKey",
    "mouseForward", "mouseCenter",
    "mouseTiltLeft", "mouseTiltRight", "mouseTiltEither",
]


class App:
    def __init__(self, store: SettingsStore | None = None):
        self.store = store or SettingsStore()
        try:
            backend = WinSpeedBackend()
        except Exception:
            backend = None
        from core.precise import SpeedBackend  # noqa: F401  (fallback when package mode)
        try:
            from core.precise import SpeedBackend as _SB
        except ImportError:
            from .core.precise import SpeedBackend as _SB
        self.precise = PreciseController(backend=backend or _SB())
        self.discovery = DiscoveryLog()
        self.hooks = HookEngine(
            router=self.route_mouse,
            key_router=self.route_key,
            discovery=self.discovery,
            swap_provider=lambda: bool(self.store.settings.swap_back_forward),
            tilt_provider=lambda: bool(self.store.settings.tilt_inverted),
        )
        self.root: tk.Tk | None = None

    # Router used by hooks and testable directly
    def route_mouse(self, button: str, is_down: bool) -> str:
        s = self.store.settings
        consuming = self.store.is_precise_trigger_consuming(button)
        action = decide_action(self.store.mapping_for(button) is not None, consuming)
        if action == "precise":
            self.precise.handle_mouse_trigger(button, is_down, s.precise_trigger,
                                              s.precise_mode, s.precise_scale, s.precise_enabled)
            return "precise"
        if action == "emit":
            if is_down:
                combo = self.store.mapping_for(button)
                if combo is not None:
                    emit(combo)
            return "emit"
        return "passthrough"

    def trigger_vk(self) -> int | None:
        s = self.store.settings
        t = s.precise_trigger
        if t == PreciseTrigger.CUSTOM_KEY.value:
            try:
                return int(s.precise_custom_vk)
            except Exception:
                return None
        for trig, vk in TRIGGER_VK.items():
            if trig.value == t:
                return int(vk)
        return None  # mouse/none triggers are not keyboard-consumable

    def route_key(self, vk: int, is_down: bool) -> bool:
        s = self.store.settings
        if not s.precise_enabled:
            return False
        want = self.trigger_vk()
        if want is None or int(vk) != int(want):
            return False
        if s.precise_mode == PreciseMode.TOGGLE.value:
            if is_down:
                self.precise.toggle(s.precise_scale, s.precise_enabled, s.precise_mode)
            return True
        if is_down:
            self.precise.hold_began(s.precise_scale, s.precise_enabled, s.precise_mode)
        else:
            self.precise.hold_ended(s.precise_mode)
        return True

    def build_ui(self) -> tk.Tk:
        root = tk.Tk()
        root.title("BSTBB700 Customizer (Win)")
        root.geometry("700x600")
        self.root = root
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        f_map = ttk.Frame(nb)
        nb.add(f_map, text="割り当て")
        self._build_mapping_tab(f_map)

        f_prec = ttk.Frame(nb)
        nb.add(f_prec, text="精密モード")
        self._build_precise_tab(f_prec)

        f_disc = ttk.Frame(nb)
        nb.add(f_disc, text="Discovery")
        self._build_discovery_tab(f_disc)
        return root

    def _build_mapping_tab(self, parent) -> None:
        ttk.Label(parent, text="未割り当ては素通し、割り当て時は横取りしてキー送信").pack(anchor="w", padx=8, pady=4)
        self._conflict_var = tk.StringVar(value=self.store.conflict_message() or "")
        ttk.Label(parent, textvariable=self._conflict_var, foreground="red",
                  wraplength=640).pack(anchor="w", padx=8)
        self._row_vars: dict = {}
        for bid, label in BUTTON_ROWS:
            frame = ttk.Frame(parent)
            frame.pack(fill="x", padx=8, pady=2)
            ttk.Label(frame, text=label, width=22).pack(side="left")
            cur = self.store.mapping_for(bid)
            txt = cur.readable() if cur else "未割り当て"
            var = tk.StringVar(value=txt)
            ttk.Label(frame, textvariable=var, width=24).pack(side="left")
            self._row_vars[bid] = var
            ttk.Button(frame, text="F13", command=lambda b=bid: self._assign_preset(b, 124, 0)).pack(side="left", padx=2)
            ttk.Button(frame, text="Ctrl+C", command=lambda b=bid: self._assign_preset(b, 67, KeyCombo.MOD_CTRL)).pack(side="left", padx=2)
            ttk.Button(frame, text="Esc", command=lambda b=bid: self._assign_preset(b, 27, 0)).pack(side="left", padx=2)
            ttk.Button(frame, text="クリア", command=lambda b=bid: self._clear(b)).pack(side="left", padx=2)
        ttk.Label(parent, text="詳細なキー選択はVK番号で指定: 例 13=Enter 91=Win").pack(anchor="w", padx=8, pady=4)
        s = self.store.settings
        self._swap_var = tk.BooleanVar(value=bool(s.swap_back_forward))
        ttk.Checkbutton(parent, text="進む/戻るを入れ替え (XBUTTON1/2逆転用)",
                        variable=self._swap_var,
                        command=lambda: self._set_swap(self._swap_var.get())).pack(anchor="w", padx=8)
        self._tilt_var = tk.BooleanVar(value=bool(s.tilt_inverted))
        ttk.Checkbutton(parent, text="チルト左右を反転 (HWHEEL符号逆転用)",
                        variable=self._tilt_var,
                        command=lambda: self._set_tilt_inv(self._tilt_var.get())).pack(anchor="w", padx=8)

    def _set_swap(self, v: bool) -> None:
        self.store.settings.swap_back_forward = bool(v)
        self.store.save()

    def _set_tilt_inv(self, v: bool) -> None:
        self.store.settings.tilt_inverted = bool(v)
        self.store.save()

    def _assign_preset(self, bid: str, vk: int, mods: int) -> None:
        self.store.set_mapping(bid, KeyCombo(vk=vk, modifiers=mods))
        self._refresh_rows()

    def _clear(self, bid: str) -> None:
        self.store.set_mapping(bid, None)
        self._refresh_rows()

    def _refresh_rows(self) -> None:
        for bid, _ in BUTTON_ROWS:
            cur = self.store.mapping_for(bid)
            self._row_vars[bid].set(cur.readable() if cur else "未割り当て")
        if hasattr(self, "_conflict_var"):
            self._conflict_var.set(self.store.conflict_message() or "")

    def _build_precise_tab(self, parent) -> None:
        s = self.store.settings
        en_var = tk.BooleanVar(value=s.precise_enabled)
        ttk.Checkbutton(parent, text="精密モードを有効化", variable=en_var,
                        command=lambda: self._set_precise_enabled(en_var.get())).pack(anchor="w", padx=8, pady=4)
        ttk.Label(parent, text="トリガー選択").pack(anchor="w", padx=8)
        trig_var = tk.StringVar(value=s.precise_trigger if s.precise_trigger in TRIGGER_CHOICES else "f13")
        combo = ttk.Combobox(parent, textvariable=trig_var, values=TRIGGER_CHOICES,
                             state="readonly", width=28)
        combo.pack(anchor="w", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._set_trigger(trig_var.get()))
        ttk.Label(parent, text="customKey用VK (例 124=F13, 20=CapsLock)").pack(anchor="w", padx=8, pady=(6, 0))
        custom_var = tk.StringVar(value=str(s.precise_custom_vk))
        ttk.Entry(parent, textvariable=custom_var, width=12).pack(anchor="w", padx=8)
        ttk.Button(parent, text="custom VK適用",
                   command=lambda: self._set_custom_vk(custom_var.get())).pack(anchor="w", padx=8, pady=2)
        ttk.Label(parent, text=f"スケール: {int(s.precise_scale*100)}% (10-100)").pack(anchor="w", padx=8)
        scale_var = tk.DoubleVar(value=s.precise_scale * 100)
        ttk.Scale(parent, from_=10, to=100, variable=scale_var, orient="horizontal",
                  command=lambda *_: self._set_scale(float(scale_var.get()) / 100)).pack(fill="x", padx=8)
        mode_var = tk.StringVar(value=s.precise_mode)
        ttk.Radiobutton(parent, text="トグル", variable=mode_var, value="toggle",
                        command=lambda: self._set_mode(mode_var.get())).pack(anchor="w", padx=8)
        hold_btn = ttk.Radiobutton(parent, text="ホールド（チルトは不可）", variable=mode_var, value="hold",
                                   command=lambda: self._set_mode(mode_var.get()))
        hold_btn.pack(anchor="w", padx=8)
        if not is_hold_capable_trigger(s.precise_trigger):
            hold_btn.configure(state="disabled")
        self._precise_hold_btn = hold_btn
        self._status_var = tk.StringVar(value="精密 ON" if self.precise.is_active else "精密 OFF")
        ttk.Label(parent, textvariable=self._status_var).pack(anchor="w", padx=8, pady=4)
        ttk.Button(parent, text="ON/OFF切替", command=lambda: self._toggle_precise()).pack(anchor="w", padx=8)
        ttk.Label(parent, text="注意: MVPはグローバル減速。全マウスとタッチパッドが減速します。").pack(anchor="w", padx=8, pady=4)

    def _set_precise_enabled(self, v: bool) -> None:
        self.store.settings.precise_enabled = bool(v)
        self.store.save()

    def _set_trigger(self, v: str) -> None:
        vals = [e.value for e in PreciseTrigger]
        if v not in vals:
            return
        self.store.settings.precise_trigger = v
        if not is_hold_capable_trigger(v) and self.store.settings.precise_mode == PreciseMode.HOLD.value:
            self.store.settings.precise_mode = PreciseMode.TOGGLE.value
        self.store.save()
        if hasattr(self, "_precise_hold_btn"):
            try:
                self._precise_hold_btn.configure(
                    state="normal" if is_hold_capable_trigger(v) else "disabled")
            except Exception:
                pass

    def _set_custom_vk(self, v: str) -> None:
        try:
            vk = int(str(v).strip())
        except Exception:
            return
        if not 1 <= vk <= 255:
            return
        self.store.settings.precise_custom_vk = vk
        self.store.save()

    def _set_scale(self, v: float) -> None:
        self.store.settings.precise_scale = min(max(float(v), 0.10), 1.0)
        self.store.save()
        if self.precise.is_active:
            self.precise.rescale(self.store.settings.precise_scale)

    def _set_mode(self, v: str) -> None:
        if v == PreciseMode.HOLD.value and not is_hold_capable_trigger(self.store.settings.precise_trigger):
            return
        self.store.settings.precise_mode = v
        self.store.save()

    def _toggle_precise(self) -> None:
        s = self.store.settings
        self.precise.toggle(s.precise_scale, s.precise_enabled, s.precise_mode)
        self._status_var.set("精密 ON" if self.precise.is_active else "精密 OFF")

    def _build_discovery_tab(self, parent) -> None:
        ttk.Label(parent, text="XBUTTON/HWHEEL/中央の実機ログ用。Win環境でボタンを押して確認").pack(anchor="w", padx=8, pady=4)
        self._disc_text = tk.Text(parent, height=16)
        self._disc_text.pack(fill="both", expand=True, padx=8)
        row = ttk.Frame(parent)
        row.pack(anchor="w", padx=8, pady=2)
        ttk.Button(row, text="更新", command=self._refresh_disc).pack(side="left", padx=2)
        ttk.Button(row, text="クリア", command=self._clear_disc).pack(side="left", padx=2)

    def _refresh_disc(self) -> None:
        self._disc_text.delete("1.0", "end")
        for line in self.discovery.lines()[-100:]:
            self._disc_text.insert("end", line + "\n")

    def _clear_disc(self) -> None:
        try:
            self.discovery.clear()
        except Exception:
            pass
        self._refresh_disc()

    def run(self) -> None:
        root = self.build_ui()
        ok = self.hooks.start()
        if not ok:
            try:
                self.discovery.add("hooks: フック開始に失敗（要管理者/除外設定）。設定変更のみ可")
            except Exception:
                pass
        try:
            root.mainloop()
        finally:
            self.precise.restore()
            self.hooks.stop()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
