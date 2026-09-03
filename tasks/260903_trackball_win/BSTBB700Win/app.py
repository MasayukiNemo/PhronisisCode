"""BSTBB700Win tkinter settings UI. Runs on Windows, importable on Mac for syntax check."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .core.discovery import DiscoveryLog
from .core.hooks import HookEngine
from .core.keys import emit
from .core.mapper import decide_action, resolve_mbutton, resolve_tilt, resolve_xbutton
from .core.precise import PreciseController, WinSpeedBackend, is_hold_capable_trigger
from .core.settings import (
    ButtonID,
    KeyCombo,
    PreciseMode,
    PreciseTrigger,
    SettingsStore,
    VK_NAMES,
)


BUTTON_ROWS = [
    ("back", "戻る (XBUTTON1)"),
    ("forward", "進む (XBUTTON2)"),
    ("center", "中央押し (MBUTTON)"),
    ("tiltLeft", "チルト左 (HWHEEL-)"),
    ("tiltRight", "チルト右 (HWHEEL+)"),
]


class App:
    def __init__(self, store: SettingsStore | None = None):
        self.store = store or SettingsStore()
        try:
            backend = WinSpeedBackend()
        except Exception:
            backend = None
        from .core.precise import SpeedBackend
        self.precise = PreciseController(backend=backend or SpeedBackend())
        self.discovery = DiscoveryLog()
        self.hooks = HookEngine(router=self.route_mouse)
        self.root: tk.Tk | None = None

    # Router used by hooks and testable directly
    def route_mouse(self, button: str, is_down: bool) -> str:
        s = self.store.settings
        consuming = self.store.is_precise_trigger_consuming(button)
        if consuming:
            self.precise.handle_mouse_trigger(button, is_down, s.precise_trigger,
                                              s.precise_mode, s.precise_scale, s.precise_enabled)
            return "precise"
        if self.store.mapping_for(button) is not None:
            if is_down:
                combo = self.store.mapping_for(button)
                if combo is not None:
                    emit(combo)
                    return "emit"
            return "emit"
        return "passthrough"

    def build_ui(self) -> tk.Tk:
        root = tk.Tk()
        root.title("BSTBB700 Customizer (Win)")
        root.geometry("680x560")
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
        ttk.Label(parent, text="詳細なキー選択はVK番号で指定: 例 13=Enter 36相当なし(Winは13) 91=Win").pack(anchor="w", padx=8, pady=4)

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

    def _build_precise_tab(self, parent) -> None:
        s = self.store.settings
        en_var = tk.BooleanVar(value=s.precise_enabled)
        ttk.Checkbutton(parent, text="精密モードを有効化", variable=en_var,
                        command=lambda: self._set_precise_enabled(en_var.get())).pack(anchor="w", padx=8, pady=4)
        ttk.Label(parent, text="トリガー: f13 / mouseForward / mouseCenter / mouseTiltLeft / mouseTiltRight / mouseTiltEither / customKey").pack(anchor="w", padx=8)
        trig_var = tk.StringVar(value=s.precise_trigger)
        ttk.Entry(parent, textvariable=trig_var, width=30).pack(anchor="w", padx=8)
        ttk.Button(parent, text="トリガー適用", command=lambda: self._set_trigger(trig_var.get())).pack(anchor="w", padx=8, pady=2)
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
        self._status_var = tk.StringVar(value="精密 OFF")
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
        self._disc_text = tk.Text(parent, height=18)
        self._disc_text.pack(fill="both", expand=True, padx=8)
        ttk.Button(parent, text="更新", command=self._refresh_disc).pack(anchor="w", padx=8, pady=2)

    def _refresh_disc(self) -> None:
        self._disc_text.delete("1.0", "end")
        for line in self.discovery.lines()[-100:]:
            self._disc_text.insert("end", line + "\n")

    def run(self) -> None:
        root = self.build_ui()
        self.hooks.start()
        try:
            root.mainloop()
        finally:
            self.precise.restore()
            self.hooks.stop()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
