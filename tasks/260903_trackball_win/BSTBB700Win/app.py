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
    from core.discovery import DiscoveryLog, default_debug_log_path
    from core.hooks import HookEngine
    from core.keys import emit
    from core.mapper import decide_action
    from core.precise import PreciseController, WinSpeedBackend, is_hold_capable_trigger
    from core.safety import EscTracker, is_from_touch, should_suppress_tilt
    from core.hud import HudController
    from core.magnifier import MAG_INTERVAL_MS, ZOOM_CHOICES, MagnifierController
    from core.tray import TrayController
    from core.settings import (
        TRIGGER_VK,
        AppSettings,
        ButtonID,
        KeyCombo,
        PreciseMode,
        PreciseTrigger,
        SettingsStore,
    )
except ImportError:  # `python -m BSTBB700Win.app` package mode
    from .core.discovery import DiscoveryLog, default_debug_log_path
    from .core.hooks import HookEngine
    from .core.keys import emit
    from .core.mapper import decide_action
    from .core.precise import PreciseController, WinSpeedBackend, is_hold_capable_trigger
    from .core.safety import EscTracker, is_from_touch, should_suppress_tilt
    from .core.hud import HudController
    from .core.magnifier import MAG_INTERVAL_MS, ZOOM_CHOICES, MagnifierController
    from .core.tray import TrayController
    from .core.settings import (
        TRIGGER_VK,
        AppSettings,
        ButtonID,
        KeyCombo,
        PreciseMode,
        PreciseTrigger,
        SettingsStore,
    )

try:
    from core.autostart import (
        is_enabled as autostart_is_enabled,
    )
    from core.autostart import (
        is_frozen as autostart_is_frozen,
    )
    from core.autostart import (
        set_enabled as autostart_set_enabled,
    )
    from core.vktable import MODIFIER_VKS, PRESETS, VK_ENTRIES, label_for, modifier_bits
except ImportError:  # package mode
    from .core.autostart import (
        is_enabled as autostart_is_enabled,
    )
    from .core.autostart import (
        is_frozen as autostart_is_frozen,
    )
    from .core.autostart import (
        set_enabled as autostart_set_enabled,
    )
    from .core.vktable import MODIFIER_VKS, PRESETS, VK_ENTRIES, label_for, modifier_bits

import tkinter as tk
from tkinter import ttk
import queue

import time
import tempfile
from pathlib import Path


def disable_flag_path() -> Path:
    base = os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
    return Path(base) / "bstbb700_disable"


BUTTON_ROWS = [
    ("back", "戻る (XBUTTON1)"),
    ("forward", "進む (XBUTTON2)"),
    ("center", "中央押し (MBUTTON)"),
    ("tiltLeft", "チルト左 (HWHEEL-)"),
    ("tiltRight", "チルト右 (HWHEEL+)"),
]

TRIGGER_CHOICES = [
    "f13", "f14", "f15", "capsLock", "customKey",
    "mouseForward", "mouseBack", "mouseCenter",
    "mouseTiltLeft", "mouseTiltRight", "mouseTiltEither",
]

TRIGGER_DISPLAYS = [PreciseTrigger(v).display for v in TRIGGER_CHOICES]
DISPLAY_TO_TRIGGER = {PreciseTrigger(v).display: v for v in TRIGGER_CHOICES}

SCALE_PRESETS = (10, 25, 50, 100)

TILT_SUPPRESS_S = 0.3

APP_VERSION = "0.2.8"


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
        self._recover_leftover_speed()
        self.hooks = HookEngine(
            router=self.route_mouse,
            key_router=self.route_key,
            discovery=self.discovery,
            swap_provider=lambda: bool(self.store.settings.swap_back_forward),
            tilt_provider=lambda: bool(self.store.settings.tilt_inverted),
            touch_filter=lambda extra: bool(is_from_touch(extra)),
        )
        self.hud = HudController()
        self.tray = TrayController()
        self.magnifier = MagnifierController(
            settings_provider=lambda: self.store.settings)
        self.esc = EscTracker()
        self._last_tilt_monotonic: float | None = None
        self._disable_flag_checked_at: float = 0.0
        self._disable_flag_cached: bool = False
        self._disable_flag_cache_init: bool = False
        self.root: tk.Tk | None = None
        # フックスレッド→UIスレッドの唯一の連絡路。tk/trayはdrain経由でのみ触る。
        self._ui_queue: queue.Queue = queue.Queue()
        self._capturing: dict | None = None
        self._capture_result: tuple | None = None
        self._capture_dialog = None

    def _reset_disable_flag_cache(self) -> None:
        self._disable_flag_cache_init = False
        self._disable_flag_cached = False

    def _recover_leftover_speed(self) -> str:
        """前回異常終了の残留低速を起動時に復元する。戻り値は表示用メモ。
        flag True = 前回ONのまま死んだ可能性 → normal_speedへ復元。
        その後、今の速度を今期のnormalとして記録する。"""
        s = self.store.settings
        note = ""
        try:
            if bool(s.precise_was_active):
                target = min(max(int(s.normal_speed), 1), 20)
                try:
                    self.precise.backend.set(target)
                    note = f"残留低速を復元した（速度{target}）"
                except Exception:
                    note = "残留低速の復元に失敗した"
                try:
                    self.discovery.add(f"startup: {note}")
                except Exception:
                    pass
            try:
                current = int(self.precise.backend.get())
            except Exception:
                current = 10
            s.normal_speed = min(max(current, 1), 20)
            s.precise_was_active = False
            self.store.save()
        except Exception:
            pass
        return note

    def _persist_precise_session(self) -> None:
        try:
            active = bool(self.precise.is_active)
            if self.store.settings.precise_was_active != active:
                self.store.settings.precise_was_active = active
                self.store.save()
        except Exception:
            pass

    def _kill_flag_active(self) -> bool:
        """%TEMP%/bstbb700_disable presence with 2s TTL cache."""
        try:
            now = time.monotonic()
        except Exception:
            now = 0.0
        try:
            if self._disable_flag_cache_init and (now - self._disable_flag_checked_at) < 2.0:
                return self._disable_flag_cached
        except Exception:
            pass
        try:
            active = bool(disable_flag_path().exists())
        except Exception:
            active = False
        self._disable_flag_cached = active
        self._disable_flag_checked_at = now
        self._disable_flag_cache_init = True
        return active

    def _post_ui(self, kind: str, **payload) -> None:
        """どのスレッドからも可。UI操作はdrainに寄せる。"""
        try:
            self._ui_queue.put_nowait((kind, payload))
        except Exception:
            pass

    def _drain_ui_queue(self) -> None:
        """UIスレッド専用。root.afterループから回す。headlessでは1回処理のみ。"""
        try:
            while True:
                try:
                    kind, payload = self._ui_queue.get_nowait()
                except Exception:
                    break
                try:
                    self._apply_ui_event(kind, payload)
                except Exception:
                    pass
        finally:
            try:
                if self.root is not None:
                    self.root.after(100, self._drain_ui_queue)
            except Exception:
                pass

    def _apply_ui_event(self, kind: str, payload: dict) -> None:
        if kind == "precise":
            try:
                if bool(self.store.settings.hud_enabled):
                    self.hud.flash(bool(payload.get("active")), float(payload.get("scale", 0.25)))
            except Exception:
                pass
            self._sync_tray_precise()
            self._sync_status_var()
        elif kind == "capture_done":
            self._refresh_rows_safe()
            self._sync_custom_vk_var()
        elif kind == "kill":
            self._sync_status_var()
            self._sync_tray_precise()
            self._sync_hook_status_var()

    def _notify_precise_changed(self) -> None:
        try:
            s = self.store.settings
            self._post_ui("precise", active=bool(self.precise.is_active),
                          scale=float(s.precise_scale))
        except Exception:
            pass

    def _sync_tray_precise(self) -> None:
        try:
            self.tray.set_precise(bool(self.precise.is_active))
        except Exception:
            pass

    def _sync_status_var(self) -> None:
        try:
            var = getattr(self, "_status_var", None)
            if var is not None:
                var.set("精密 ON" if self.precise.is_active else "精密 OFF")
        except Exception:
            pass

    def _fire_kill_switch(self) -> None:
        # 入力復旧のため停止は即実行（どのスレッドでも安全な操作のみ）。
        # UI同期はdrainに回す。tk/trayには触らない。
        try:
            self.precise.set_active(False, 1.0)
        except Exception:
            pass
        try:
            self.hooks.stop()
        except Exception:
            pass
        try:
            self.discovery.add("kill-switch: Esc連打でフック停止（設定画面から再開可）")
        except Exception:
            pass
        self._persist_precise_session()
        self._post_ui("kill")

    # Router used by hooks and testable directly
    def route_mouse(self, button: str, is_down: bool) -> str:
        if self._kill_flag_active():
            return "passthrough"
        if button in (ButtonID.TILT_LEFT.value, ButtonID.TILT_RIGHT.value):
            try:
                now = time.monotonic()
            except Exception:
                now = 0.0
            if self._last_tilt_monotonic is not None and should_suppress_tilt(
                    self._last_tilt_monotonic, now, TILT_SUPPRESS_S):
                return "passthrough"
            self._last_tilt_monotonic = now
        s = self.store.settings
        before = bool(self.precise.is_active)
        consuming = self.store.is_precise_trigger_consuming(button)
        action = decide_action(self.store.mapping_for(button) is not None, consuming)
        if action == "precise":
            self.precise.handle_mouse_trigger(button, is_down, s.precise_trigger,
                                              s.precise_mode, s.precise_scale, s.precise_enabled)
            if bool(self.precise.is_active) != before:
                self._persist_precise_session()
                self._notify_precise_changed()
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
        if self._kill_flag_active():
            return False
        if self._capturing is not None:
            return self._handle_capture_key(int(vk), bool(is_down))
        if int(vk) == 27 and bool(is_down):
            try:
                fired = self.esc.push(time.monotonic())
            except Exception:
                fired = False
            if fired:
                self._fire_kill_switch()
                return True
        s = self.store.settings
        if not s.precise_enabled:
            return False
        want = self.trigger_vk()
        if want is None or int(vk) != int(want):
            return False
        before = bool(self.precise.is_active)
        if s.precise_mode == PreciseMode.TOGGLE.value:
            if is_down:
                self.precise.toggle(s.precise_scale, s.precise_enabled, s.precise_mode)
            consumed = True
        else:
            if is_down:
                self.precise.hold_began(s.precise_scale, s.precise_enabled, s.precise_mode)
            else:
                self.precise.hold_ended(s.precise_mode)
            consumed = True
        if bool(self.precise.is_active) != before:
            self._persist_precise_session()
            self._notify_precise_changed()
        return consumed

    def _live_modifier_bits(self) -> int:
        """Read Ctrl/Shift/Alt/Win via GetKeyState. Delayed call, Mac-safe (0)."""
        try:
            try:
                from .core.winapi import user32
            except ImportError:
                from core.winapi import user32

            def _down(vk: int) -> bool:
                try:
                    return bool(user32.GetKeyState(int(vk)) & 0x8000)
                except Exception:
                    return False

            return modifier_bits({
                "ctrl": _down(162) or _down(163),
                "shift": _down(160) or _down(161),
                "alt": _down(164) or _down(165),
                "win": _down(91) or _down(92),
            })
        except Exception:
            return 0

    def _handle_capture_key(self, vk: int, is_down: bool) -> bool:
        """Single branch point for capture: Esc cancels, others are recorded.

        Modifier-only keydown is swallowed without recording so that
        Ctrl+C style combos can be captured (the Ctrl down arrives first).
        """
        if not is_down:
            return True
        if int(vk) == 27:
            self._capturing = None
            self._capture_result = None
            return True
        if int(vk) in MODIFIER_VKS:
            return True
        mods = self._live_modifier_bits()
        cap = self._capturing or {}
        kind = cap.get("kind")
        button = cap.get("button")
        self._capture_result = (int(vk), int(mods))
        self._capturing = None
        if kind == "map" and button:
            self.store.set_mapping(button, KeyCombo(vk=int(vk), modifiers=int(mods)))
        elif kind == "custom":
            self.store.settings.precise_custom_vk = int(vk)
            self.store.settings.precise_trigger = PreciseTrigger.CUSTOM_KEY.value
            self.store.save()
        self._post_ui("capture_done")
        return True

    def build_ui(self) -> tk.Tk:
        root = tk.Tk()
        root.title(f"BSTBB700 Customizer (Win) {APP_VERSION}")
        root.geometry("700x600")
        self.root = root
        try:
            self.hud.attach(root)
        except Exception:
            pass
        try:
            if bool(self.store.settings.debug_log_enabled):
                self.discovery.set_debug_file(default_debug_log_path())
            else:
                self.discovery.set_debug_file(None)
        except Exception:
            pass
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

        f_gen = ttk.Frame(nb)
        nb.add(f_gen, text="一般")
        self._build_general_tab(f_gen)
        return root

    def _build_mapping_tab(self, parent) -> None:
        ttk.Label(parent, text="未割り当ては素通し、割り当て時は横取りしてキー送信").pack(anchor="w", padx=8, pady=4)
        ttk.Label(parent, text="※ Escはキャプチャ不可（押すと取消）。Escの割当はビルダーで割当可",
                  wraplength=640).pack(anchor="w", padx=8)
        self._conflict_var = tk.StringVar(value=self.store.conflict_message() or "")
        ttk.Label(parent, textvariable=self._conflict_var, foreground="red",
                  wraplength=640).pack(anchor="w", padx=8)
        self._row_vars: dict = {}
        self._builder_frames: dict = {}
        self._mod_vars: dict = {}
        self._key_vars: dict = {}
        self._preset_vars: dict = {}
        for bid, label in BUTTON_ROWS:
            frame = ttk.Frame(parent)
            frame.pack(fill="x", padx=8, pady=2)
            ttk.Label(frame, text=label, width=22).pack(side="left")
            cur = self.store.mapping_for(bid)
            txt = cur.readable() if cur else "未割り当て"
            var = tk.StringVar(value=txt)
            ttk.Label(frame, textvariable=var, width=24).pack(side="left")
            self._row_vars[bid] = var
            ttk.Button(frame, text="キャプチャ",
                       command=lambda b=bid: self._start_capture("map", b)).pack(side="left", padx=2)
            ttk.Button(frame, text="組み立て",
                       command=lambda b=bid: self._toggle_builder(b)).pack(side="left", padx=2)
            ttk.Button(frame, text="クリア", command=lambda b=bid: self._clear(b)).pack(side="left", padx=2)
            self._build_builder(parent, bid)
        ttk.Label(parent, text="詳細なキー選択はビルダーで指定（vktable一覧）").pack(anchor="w", padx=8, pady=4)
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

    def _clear(self, bid: str) -> None:
        self.store.set_mapping(bid, None)
        self._refresh_rows_safe()

    def _vk_display(self, vk: int) -> str:
        return f"{label_for(vk)} (VK{vk})"

    def _build_builder(self, parent, bid: str) -> None:
        box = ttk.Frame(parent)
        mods = {
            "ctrl": tk.BooleanVar(value=False),
            "shift": tk.BooleanVar(value=False),
            "alt": tk.BooleanVar(value=False),
            "win": tk.BooleanVar(value=False),
        }
        self._mod_vars[bid] = mods
        row = ttk.Frame(box)
        row.pack(fill="x", padx=4)
        for key, text in (("ctrl", "Ctrl"), ("shift", "Shift"), ("alt", "Alt"), ("win", "Win")):
            ttk.Checkbutton(row, text=text, variable=mods[key]).pack(side="left")
        key_var = tk.StringVar(value=self._vk_display(VK_ENTRIES[0][0]) if VK_ENTRIES else "")
        ttk.Combobox(box, textvariable=key_var,
                     values=[self._vk_display(vk) for vk, _label, _group in VK_ENTRIES],
                     state="readonly", width=28).pack(anchor="w", padx=4)
        self._key_vars[bid] = key_var
        preset_var = tk.StringVar(value=PRESETS[0][0] if PRESETS else "")
        pcombo = ttk.Combobox(box, textvariable=preset_var,
                              values=[name for name, _vk, _mods in PRESETS],
                              state="readonly", width=28)
        pcombo.pack(anchor="w", padx=4)
        pcombo.bind("<<ComboboxSelected>>", lambda _e, b=bid: self._apply_preset_to_builder(b))
        self._preset_vars[bid] = preset_var
        ttk.Button(box, text="反映", command=lambda b=bid: self._apply_builder(b)).pack(anchor="w", padx=4, pady=2)
        self._builder_frames[bid] = box

    def _toggle_builder(self, bid: str) -> None:
        box = self._builder_frames.get(bid)
        if box is None:
            return
        try:
            if box.winfo_manager():
                box.pack_forget()
            else:
                box.pack(fill="x", padx=24, pady=2)
        except Exception:
            pass

    def _apply_preset_to_builder(self, bid: str) -> None:
        name = self._preset_vars[bid].get()
        for pname, pvk, pmods in PRESETS:
            if pname != name:
                continue
            if pvk is None:
                # 「未割り当て」選択はビルダー転記ではなくクリア扱いと明示
                self._clear(bid)
                return
            self._mod_vars[bid]["ctrl"].set(bool(pmods & KeyCombo.MOD_CTRL))
            self._mod_vars[bid]["shift"].set(bool(pmods & KeyCombo.MOD_SHIFT))
            self._mod_vars[bid]["alt"].set(bool(pmods & KeyCombo.MOD_ALT))
            self._mod_vars[bid]["win"].set(bool(pmods & KeyCombo.MOD_WIN))
            if pvk is not None:
                self._key_vars[bid].set(self._vk_display(pvk))
            break

    def _apply_builder(self, bid: str) -> None:
        disp = self._key_vars[bid].get()
        vk: int | None = None
        if "(VK" in disp and disp.endswith(")"):
            try:
                vk = int(disp.rsplit("(VK", 1)[1][:-1])
            except Exception:
                vk = None
        if vk is None:
            for v, lab, _group in VK_ENTRIES:
                if lab == disp:
                    vk = v
                    break
        if vk is None:
            return
        mods = 0
        if self._mod_vars[bid]["ctrl"].get():
            mods |= KeyCombo.MOD_CTRL
        if self._mod_vars[bid]["shift"].get():
            mods |= KeyCombo.MOD_SHIFT
        if self._mod_vars[bid]["alt"].get():
            mods |= KeyCombo.MOD_ALT
        if self._mod_vars[bid]["win"].get():
            mods |= KeyCombo.MOD_WIN
        self.store.set_mapping(bid, KeyCombo(vk=int(vk), modifiers=int(mods)))
        self._refresh_rows()

    CAPTURE_POLL_MS = 120

    def _close_capture_dialog(self) -> None:
        """キャプチャダイアログの後片付け集約点。状態(_capturing)は触らない。"""
        dlg, self._capture_dialog = self._capture_dialog, None
        if dlg is None:
            return
        try:
            dlg.grab_release()
        except Exception:
            pass
        try:
            dlg.destroy()
        except Exception:
            pass

    def _start_capture(self, kind: str, button: str | None = None) -> None:
        self._close_capture_dialog()  # 多重起動時は既存を先に片付ける
        self._capturing = {"kind": kind, "button": button}
        self._capture_result = None
        if self.root is None:
            return
        try:
            dlg = tk.Toplevel(self.root)
        except Exception:
            self._capturing = None  # 生成失敗時は残留させない
            return
        self._capture_dialog = dlg
        dlg.title("キーキャプチャ")
        try:
            dlg.transient(self.root)
            dlg.grab_set()
        except Exception:
            pass
        ttk.Label(dlg, text="押したキーを取得中…Escで取消").pack(padx=16, pady=8)
        ttk.Label(dlg, text="※ 修飾は同時押しで合成（Ctrl+C可）。Esc自体は記録不可。Escの割当はビルダーで行う").pack(padx=16)
        ttk.Button(dlg, text="取消", command=self._cancel_capture, takefocus=False).pack(pady=8)
        try:
            dlg.protocol("WM_DELETE_WINDOW", self._cancel_capture)
        except Exception:
            pass
        self._poll_capture_dialog(dlg)

    def _cancel_capture(self) -> None:
        # 記録済み（Enter/Spaceで確定後に取消ボタンが誤発火）の場合は結果を守る
        if self._capturing is not None:
            self._capturing = None
            self._capture_result = None
        self._close_capture_dialog()
        self._refresh_rows_safe()

    def _poll_capture_dialog(self, dlg) -> None:
        """終了検知後のdestroy専用。取消・確定の後片付けは_close_capture_dialog側。"""
        try:
            if self._capturing is not None and dlg.winfo_exists():
                dlg.after(self.CAPTURE_POLL_MS, lambda: self._poll_capture_dialog(dlg))
                return
        except Exception:
            pass
        if getattr(self, "_capture_dialog", None) is dlg:
            self._close_capture_dialog()
        self._refresh_rows_safe()
        self._sync_custom_vk_var()

    def _refresh_rows(self) -> None:
        for bid, _ in BUTTON_ROWS:
            cur = self.store.mapping_for(bid)
            self._row_vars[bid].set(cur.readable() if cur else "未割り当て")
        if hasattr(self, "_conflict_var"):
            self._conflict_var.set(self.store.conflict_message() or "")

    def _refresh_rows_safe(self) -> None:
        if getattr(self, "_row_vars", None) is None:
            return
        if self.root is None:
            return  # headlessではUI更新不要
        self._refresh_rows()

    def _sync_custom_vk_var(self) -> None:
        var = getattr(self, "_custom_vk_var", None)
        if var is None:
            return
        try:
            var.set(str(self.store.settings.precise_custom_vk))
        except Exception:
            pass  # UI反映失敗に限定して吸収

    def _build_precise_tab(self, parent) -> None:
        s = self.store.settings
        en_var = tk.BooleanVar(value=s.precise_enabled)
        ttk.Checkbutton(parent, text="精密モードを有効化", variable=en_var,
                        command=lambda: self._set_precise_enabled(en_var.get())).pack(anchor="w", padx=8, pady=4)
        ttk.Label(parent, text="トリガー選択").pack(anchor="w", padx=8)
        cur_trig = s.precise_trigger if s.precise_trigger in TRIGGER_CHOICES else "f13"
        trig_var = tk.StringVar(value=PreciseTrigger(cur_trig).display)
        combo = ttk.Combobox(parent, textvariable=trig_var, values=TRIGGER_DISPLAYS,
                             state="readonly", width=28)
        combo.pack(anchor="w", padx=8)
        combo.bind("<<ComboboxSelected>>",
                   lambda _e: self._set_trigger(DISPLAY_TO_TRIGGER.get(trig_var.get(), "f13")))
        ttk.Label(parent, text="customKey用VK (例 124=F13, 20=CapsLock)").pack(anchor="w", padx=8, pady=(6, 0))
        custom_var = tk.StringVar(value=str(s.precise_custom_vk))
        self._custom_vk_var = custom_var
        ttk.Entry(parent, textvariable=custom_var, width=12).pack(anchor="w", padx=8)
        ttk.Button(parent, text="custom VK適用",
                   command=lambda: self._set_custom_vk(custom_var.get())).pack(anchor="w", padx=8, pady=2)
        ttk.Button(parent, text="キャプチャで設定",
                   command=lambda: self._start_capture("custom")).pack(anchor="w", padx=8, pady=2)
        self._scale_label_var = tk.StringVar(value=self._scale_label_text())
        ttk.Label(parent, textvariable=self._scale_label_var).pack(anchor="w", padx=8)
        self._scale_var = tk.DoubleVar(value=s.precise_scale * 100)
        ttk.Scale(parent, from_=10, to=100, variable=self._scale_var, orient="horizontal",
                  command=lambda *_: self._apply_scale_percent(float(self._scale_var.get()))).pack(fill="x", padx=8)
        srow = ttk.Frame(parent)
        srow.pack(anchor="w", padx=8, pady=2)
        for pct in SCALE_PRESETS:
            ttk.Button(srow, text=f"{pct}%",
                       command=lambda p=pct: self._apply_scale_percent(float(p))).pack(side="left", padx=2)
        self._scale_entry_var = tk.StringVar(value=str(int(s.precise_scale * 100)))
        ttk.Entry(srow, textvariable=self._scale_entry_var, width=6).pack(side="left", padx=2)
        ttk.Button(srow, text="適用",
                   command=lambda: self._apply_scale_entry(self._scale_entry_var.get())).pack(side="left", padx=2)
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
        hud_var = tk.BooleanVar(value=bool(s.hud_enabled))
        ttk.Checkbutton(parent, text="切替時にHUD表示する",
                        variable=hud_var,
                        command=lambda: self._set_hud_enabled(hud_var.get())).pack(anchor="w", padx=8)
        mag_var = tk.BooleanVar(value=bool(s.magnifier_enabled))
        ttk.Checkbutton(parent, text="精密ON中に拡大鏡を表示する（カーソル右斜め上）",
                        variable=mag_var,
                        command=lambda: self._set_magnifier_enabled(mag_var.get())).pack(anchor="w", padx=8)
        ttk.Label(parent, text="拡大鏡の倍率").pack(anchor="w", padx=8)
        zoom_var = tk.StringVar(value=f"{int(s.magnifier_zoom)}倍")
        zoom_combo = ttk.Combobox(parent, textvariable=zoom_var,
                                  values=[f"{z}倍" for z in ZOOM_CHOICES],
                                  state="readonly", width=10)
        zoom_combo.pack(anchor="w", padx=8)
        zoom_combo.bind("<<ComboboxSelected>>",
                        lambda _e: self._set_magnifier_zoom(zoom_var.get()))
        ttk.Label(parent, text="拡大鏡の大きさ").pack(anchor="w", padx=8)
        self._mag_size_var = tk.DoubleVar(value=float(s.magnifier_size))
        ttk.Scale(parent, from_=48, to=480, variable=self._mag_size_var, orient="horizontal",
                  command=lambda *_: self._set_magnifier_size(float(self._mag_size_var.get()))).pack(fill="x", padx=8)
        self._mag_status_var = tk.StringVar(value="拡大鏡: 停止中")
        ttk.Label(parent, textvariable=self._mag_status_var, wraplength=640).pack(anchor="w", padx=8)
        ttk.Label(parent, text="注意: MVPはグローバル減速。全マウスとタッチパッドが減速します。").pack(anchor="w", padx=8, pady=4)

    def _set_precise_enabled(self, v: bool) -> None:
        self.store.settings.precise_enabled = bool(v)
        self.store.save()

    def _set_hud_enabled(self, v: bool) -> None:
        self.store.settings.hud_enabled = bool(v)
        self.store.save()

    def _set_magnifier_enabled(self, v: bool) -> None:
        self.store.settings.magnifier_enabled = bool(v)
        self.store.save()

    def _set_magnifier_zoom(self, v: str) -> None:
        try:
            z = int(str(v).replace("倍", "").strip())
        except Exception:
            return
        if z not in ZOOM_CHOICES:
            return
        self.store.settings.magnifier_zoom = z
        self.store.save()

    def _set_magnifier_size(self, v: float) -> None:
        try:
            size = int(round(float(v)))
        except Exception:
            return
        self.store.settings.magnifier_size = min(max(size, 48), 480)
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
        """custom VK手入力。キャプチャ時と揃え、triggerもcustomKeyへ切替える。"""
        try:
            vk = int(str(v).strip())
        except Exception:
            return
        if not 1 <= vk <= 255:
            return
        self.store.settings.precise_custom_vk = vk
        self.store.settings.precise_trigger = PreciseTrigger.CUSTOM_KEY.value
        self.store.save()

    def _scale_label_text(self) -> str:
        try:
            pct = int(round(float(self.store.settings.precise_scale) * 100))
        except Exception:
            pct = 25
        return f"スケール: {pct}% (10-100)"

    def _sync_scale_widgets(self) -> None:
        try:
            pct = min(max(float(self.store.settings.precise_scale) * 100, 10.0), 100.0)
        except Exception:
            return
        for name, val in (("_scale_var", pct), ("_scale_entry_var", str(int(round(pct))))):
            try:
                var = getattr(self, name, None)
                if var is not None:
                    var.set(val)
            except Exception:
                pass
        try:
            if getattr(self, "_scale_label_var", None) is not None:
                self._scale_label_var.set(self._scale_label_text())
        except Exception:
            pass

    def _apply_scale_percent(self, pct: float) -> None:
        """スケール操作の単一窓口（スライダー・プリセット・数値の合流点）。"""
        try:
            p = float(pct)
        except Exception:
            return
        p = min(max(p, 10.0), 100.0)
        self._set_scale(p / 100.0)
        self._sync_scale_widgets()

    def _apply_scale_entry(self, v: str) -> None:
        try:
            self._apply_scale_percent(float(str(v).strip().rstrip("%")))
        except Exception:
            self._sync_scale_widgets()

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
        # UIスレッド専用（ボタン/tray-after経由）。フックスレッドからは呼ばない。
        s = self.store.settings
        before = bool(self.precise.is_active)
        self.precise.toggle(s.precise_scale, s.precise_enabled, s.precise_mode)
        self._persist_precise_session()
        self._sync_status_var()
        if bool(self.precise.is_active) != before:
            self._flash_hud_direct()

    def _flash_hud_direct(self) -> None:
        # UIスレッド専用。フックスレッドからは _notify_precise_changed を使う。
        try:
            if bool(self.store.settings.hud_enabled):
                s = self.store.settings
                self.hud.flash(bool(self.precise.is_active), float(s.precise_scale))
        except Exception:
            pass
        self._sync_tray_precise()

    def _build_discovery_tab(self, parent) -> None:
        ttk.Label(parent, text="XBUTTON/HWHEEL/中央の実機ログ用。Win環境でボタンを押して確認").pack(anchor="w", padx=8, pady=4)
        self._disc_text = tk.Text(parent, height=16)
        self._disc_text.pack(fill="both", expand=True, padx=8)
        row = ttk.Frame(parent)
        row.pack(anchor="w", padx=8, pady=2)
        ttk.Button(row, text="更新", command=self._refresh_disc).pack(side="left", padx=2)
        ttk.Button(row, text="クリア", command=self._clear_disc).pack(side="left", padx=2)
        ttk.Button(row, text="フック再開", command=self._restart_hooks).pack(side="left", padx=2)
        self._hook_status_var = tk.StringVar(value=self._hook_status_text())
        ttk.Label(row, textvariable=self._hook_status_var).pack(side="left", padx=8)
        self._debug_var = tk.BooleanVar(value=bool(self.store.settings.debug_log_enabled))
        ttk.Checkbutton(parent, text="デバッグログをファイル出力 (%TEMP%/bstbb700_debug.log)",
                        variable=self._debug_var,
                        command=lambda: self._set_debug_log(self._debug_var.get())).pack(anchor="w", padx=8)

    def _hook_status_text(self) -> str:
        try:
            if self._kill_flag_active():
                return "フック停止中（無効化フラグあり）"
            running = bool(self.hooks.running)
        except Exception:
            running = False
        return "フック動作中" if running else "フック停止中"

    def _sync_hook_status_var(self) -> None:
        try:
            var = getattr(self, "_hook_status_var", None)
            if var is not None:
                var.set(self._hook_status_text())
        except Exception:
            pass

    def _restart_hooks(self) -> None:
        try:
            ok = bool(self.hooks.start())
        except Exception:
            ok = False
        try:
            self.discovery.add("フック再開: " + ("成功" if ok else "失敗"))
            if ok and self._kill_flag_active():
                self.discovery.add("注意: 無効化フラグファイルが残っているため素通し継続。外して再開すること")
        except Exception:
            pass
        self._sync_hook_status_var()
        self._refresh_disc()

    def _refresh_disc(self) -> None:
        if getattr(self, "_disc_text", None) is None:
            return
        if self.root is None:
            return
        self._disc_text.delete("1.0", "end")
        for line in self.discovery.lines()[-100:]:
            self._disc_text.insert("end", line + "\n")
        self._sync_hook_status_var()

    def _clear_disc(self) -> None:
        try:
            self.discovery.clear()
        except Exception:
            pass
        self._refresh_disc()

    def _set_debug_log(self, v: bool) -> None:
        on = bool(v)
        try:
            self.store.settings.debug_log_enabled = on
            self.store.save()
        except Exception:
            pass
        try:
            self.discovery.set_debug_file(default_debug_log_path() if on else None)
        except Exception:
            pass

    def _build_general_tab(self, parent) -> None:
        ttk.Label(parent, text=f"BSTBB700Win {APP_VERSION}").pack(anchor="w", padx=8, pady=4)
        self._speed_var = tk.StringVar(value=self._speed_text())
        ttk.Label(parent, textvariable=self._speed_var, wraplength=640).pack(anchor="w", padx=8)
        ttk.Button(parent, text="速度表示を更新・通常に戻す",
                   command=self._restore_normal_speed).pack(anchor="w", padx=8, pady=2)
        try:
            auto_on = bool(autostart_is_enabled())
        except Exception:
            auto_on = False
        try:
            frozen = bool(autostart_is_frozen())
        except Exception:
            frozen = False
        self._autostart_var = tk.BooleanVar(value=auto_on)
        self._autostart_msg = tk.StringVar(value="")
        auto_cb = ttk.Checkbutton(parent, text="Windows起動時に自動起動（レジストリRun）",
                                  variable=self._autostart_var,
                                  command=lambda: self._toggle_autostart())
        auto_cb.pack(anchor="w", padx=8)
        if not frozen:
            try:
                auto_cb.configure(state="disabled")
            except Exception:
                pass
            ttk.Label(parent, text="開発実行中は登録不可（凍結exeのみ登録可）").pack(anchor="w", padx=8)
        elif os.name != "nt":
            try:
                auto_cb.configure(state="disabled")
            except Exception:
                pass
            ttk.Label(parent, text="Windows以外では自動起動に未対応").pack(anchor="w", padx=8)
        ttk.Label(parent, textvariable=self._autostart_msg, wraplength=640).pack(anchor="w", padx=8)
        ttk.Label(parent, text="垂直ホイールは素通し（カスタム対象外）。水平チルトのみ割当対象。",
                  wraplength=640).pack(anchor="w", padx=8, pady=4)
        ttk.Label(parent, text="AV/SmartScreen案内: フック+SendInputのため誤検知時は除外設定を行うこと。"
                  "署名なしMVPのためSmartScreen警告時は「詳細情報→実行」。",
                  wraplength=640).pack(anchor="w", padx=8, pady=4)
        ttk.Button(parent, text="設定フォルダを開く",
                   command=self._open_settings_folder).pack(anchor="w", padx=8, pady=2)
        ttk.Button(parent, text="設定リセット",
                   command=self._reset_settings).pack(anchor="w", padx=8, pady=2)
        self._general_msg = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self._general_msg, wraplength=640).pack(anchor="w", padx=8)

    def _speed_text(self) -> str:
        try:
            cur = int(self.precise.backend.get())
        except Exception:
            cur = -1
        try:
            normal = int(self.store.settings.normal_speed)
        except Exception:
            normal = 10
        state = "精密ON" if bool(self.precise.is_active) else "精密OFF"
        return f"マウス速度: 現在 {cur} / 通常 {normal}（{state}）"

    def _restore_normal_speed(self) -> None:
        try:
            target = min(max(int(self.store.settings.normal_speed), 1), 20)
        except Exception:
            target = 10
        try:
            self.precise.backend.set(target)
            self.precise.is_active = False
            self.precise.is_hold_pressed = False
            self._persist_precise_session()
            msg = f"速度を通常（{target}）に戻した"
        except Exception as e:
            msg = f"速度の復元に失敗: {e}"
        try:
            self._general_msg.set(msg)
        except Exception:
            pass
        try:
            self._speed_var.set(self._speed_text())
        except Exception:
            pass
        self._sync_status_var()
        self._sync_tray_precise()

    def _toggle_autostart(self) -> None:
        try:
            ok, msg = autostart_set_enabled(bool(self._autostart_var.get()))
        except Exception as e:
            ok, msg = False, str(e)
        try:
            self._autostart_msg.set(msg)
            self._autostart_var.set(bool(autostart_is_enabled()))
        except Exception:
            pass

    def _open_settings_folder(self) -> None:
        try:
            folder = str(self.store.path.parent)
            if os.name == "nt":
                os.startfile(folder)  # noqa: PGH121 - Windows-only, guarded
            else:
                self._general_msg.set(f"設定: {self.store.path}")
        except Exception as e:
            try:
                self._general_msg.set(f"フォルダを開けない: {e}")
            except Exception:
                pass

    def _reset_settings(self) -> None:
        try:
            from tkinter import messagebox
            if self.root is not None:
                if not messagebox.askyesno("確認", "全割当と精密設定を初期化します。よろしいですか。"):
                    return
        except Exception:
            pass
        try:
            self.precise.restore()
        except Exception:
            pass
        ok = False
        try:
            try:
                self.store.path.unlink()
            except Exception:
                pass
            self.store.settings = AppSettings()
            self.store.save()
            ok = bool(self.store.path.exists())
        except Exception:
            ok = False
        self._refresh_rows_safe()
        try:
            if hasattr(self, "_status_var"):
                self._status_var.set("精密 OFF")
        except Exception:
            pass
        try:
            dbg = getattr(self, "_debug_var", None)
            if dbg is not None:
                dbg.set(bool(self.store.settings.debug_log_enabled))
        except Exception:
            pass
        try:
            self.discovery.set_debug_file(
                default_debug_log_path() if bool(self.store.settings.debug_log_enabled) else None)
        except Exception:
            pass
        try:
            if hasattr(self, "_swap_var"):
                self._swap_var.set(bool(self.store.settings.swap_back_forward))
            if hasattr(self, "_tilt_var"):
                self._tilt_var.set(bool(self.store.settings.tilt_inverted))
            if hasattr(self, "_autostart_var"):
                self._autostart_var.set(bool(autostart_is_enabled()))
            self._general_msg.set("設定をリセットした" if ok else "リセットに失敗した")
        except Exception:
            pass

    def _bring_to_front(self) -> None:
        try:
            if self.root is None:
                return
            self.root.deiconify()
            self.root.lift()
            try:
                self.root.focus_force()
            except Exception:
                pass
        except Exception:
            pass

    def _quit_from_tray(self) -> None:
        try:
            if self.root is None:
                return
            self.root.quit()
            try:
                self.root.destroy()
            except Exception:
                pass
        except Exception:
            pass

    def _mag_tick(self) -> None:
        """UIスレッド専用。精密ON中のみ拡大鏡を追従表示する。"""
        try:
            self.magnifier.tick(self.root, bool(self.precise.is_active))
        except Exception:
            pass
        try:
            var = getattr(self, "_mag_status_var", None)
            if var is not None:
                var.set(self.magnifier.status_text())
        except Exception:
            pass
        finally:
            try:
                if self.root is not None:
                    self.root.after(MAG_INTERVAL_MS, self._mag_tick)
            except Exception:
                pass

    def hook_error_text(self) -> str:
        try:
            detail = (getattr(self.hooks, "last_error", None) or "").strip()
        except Exception:
            detail = ""
        base = "hooks: フック開始に失敗（要管理者/除外設定）。設定変更のみ可"
        return base + (f" 原因: {detail}" if detail else "")

    def run(self) -> None:
        try:
            try:
                from .core.winapi import enable_dpi_awareness
            except ImportError:
                from core.winapi import enable_dpi_awareness
            mode = enable_dpi_awareness()
        except Exception:
            mode = "error"
        try:
            self.discovery.add(f"dpi-awareness: {mode}")
        except Exception:
            pass
        root = self.build_ui()
        try:
            root.after(100, self._drain_ui_queue)
        except Exception:
            pass
        try:
            root.after(MAG_INTERVAL_MS, self._mag_tick)
        except Exception:
            pass
        try:
            ok_tray = self.tray.start(
                on_show=lambda: root.after(0, self._bring_to_front),
                on_toggle_precise=lambda: root.after(0, self._toggle_precise),
                on_quit=lambda: root.after(0, self._quit_from_tray),
            )
        except Exception:
            ok_tray = False
        if not ok_tray:
            try:
                self.discovery.add("tray: 常駐アイコンを開始できず窓常駐に縮退")
            except Exception:
                pass
        ok = self.hooks.start()
        if not ok:
            try:
                self.discovery.add(self.hook_error_text())
            except Exception:
                pass
        try:
            root.mainloop()
        finally:
            try:
                self.tray.stop()
            except Exception:
                pass
            self.precise.restore()
            self.hooks.stop()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
