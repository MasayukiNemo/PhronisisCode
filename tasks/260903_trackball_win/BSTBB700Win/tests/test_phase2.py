"""Phase2 tests. Mac-runnable, no mainloop (unit only)."""
import os
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import app as appmod
import core.hud as hudmod
import core.tray as traymod
from core.discovery import DiscoveryLog
from core.hooks import HookEngine
from core.hud import HudController
from core.safety import EscTracker, is_from_touch, should_suppress_tilt
from core.settings import KeyCombo, SettingsStore
from core.tray import MENU_QUIT_ID, MENU_SHOW_ID, MENU_TOGGLE_ID, precise_icon_id


def _fresh_app():
    d = tempfile.mkdtemp(prefix="bstbb700_win_phase2_")
    p = pathlib.Path(d) / "settings.json"
    os.environ["BSTBB700_SETTINGS_PATH"] = str(p)
    a = appmod.App(store=SettingsStore(path=p))
    try:
        fp = appmod.disable_flag_path()
        if fp.exists():
            fp.unlink()
    except Exception:
        pass
    return a


# ---- HUD ----
def test_hud_headless_noop():
    h = HudController()
    h.flash(True, 0.25)
    h.flash(False, 1.0)
    h.hide()


def test_hud_flash_defers_via_after():
    class DummyRoot:
        def __init__(self):
            self.calls = []

        def after(self, ms, fn):
            self.calls.append((ms, fn))
            return len(self.calls)

    h = HudController()
    root = DummyRoot()
    h.attach(root)
    h.flash(True, 0.25)
    assert any(ms == 0 for ms, _fn in root.calls)
    h.hide()
    assert any(ms == 0 for ms, _fn in root.calls)


def test_hud_reflash_single_timer():
    class FakeWin:
        def __init__(self):
            self.destroyed = False

        def winfo_exists(self):
            return not self.destroyed

        def overrideredirect(self, _v):
            pass

        def attributes(self, *_a):
            pass

        def config(self, **_k):
            pass

        def geometry(self, _s):
            pass

        def destroy(self):
            self.destroyed = True

    class FakeLabel:
        def __init__(self):
            self.texts = []

        def config(self, **kw):
            self.texts.append(kw.get("text"))

        def pack(self):
            pass

    made = {}

    class FakeTk:
        @staticmethod
        def Toplevel(_root):
            w = FakeWin()
            made["win"] = w
            return w

        @staticmethod
        def Label(_w, **_kw):
            lab = FakeLabel()
            made["lab"] = lab
            return lab

    class FakeRoot:
        def __init__(self):
            self.calls = []

        def after(self, ms, fn):
            self.calls.append(ms)
            if ms == 0:
                fn()
                return 1
            return len(self.calls)

        def after_cancel(self, _i):
            pass

        def winfo_screenwidth(self):
            return 1920

    old = hudmod.tk
    hudmod.tk = FakeTk
    try:
        h = HudController()
        root = FakeRoot()
        h.attach(root)
        h.flash(True, 0.25)
        h.flash(False, 0.5)
        assert root.calls.count(1500) == 1
        assert made["lab"].texts and "OFF" in made["lab"].texts[-1]
    finally:
        hudmod.tk = old


# ---- tray ----
def test_tray_nonwindows_noop():
    old = traymod.is_windows
    traymod.is_windows = lambda: False
    try:
        t = traymod.TrayController()
        assert t.start(on_show=None, on_toggle_precise=None, on_quit=None) is False
        assert t.is_active is False
        t.set_precise(True)  # no-op, must not raise
        t.stop()
    finally:
        traymod.is_windows = old


def test_tray_icon_selection():
    assert precise_icon_id(True) != precise_icon_id(False)
    assert precise_icon_id(True) == traymod.IDI_INFORMATION
    assert precise_icon_id(False) == traymod.IDI_APPLICATION
    assert len({MENU_SHOW_ID, MENU_TOGGLE_ID, MENU_QUIT_ID}) == 3
    assert traymod.precise_tooltip(True) != traymod.precise_tooltip(False)


# ---- safety ----
def test_is_from_touch():
    assert is_from_touch(0xFF515700) is True
    assert is_from_touch(0xFF515701) is True  # low byte ignored
    assert is_from_touch(0) is False
    assert is_from_touch(0x00005700) is False  # low bytes only, no signature


def test_esc_tracker_fires_on_fifth_and_resets():
    tr = EscTracker(window=2.0, threshold=5)
    base = 1000.0
    assert [tr.push(base + i * 0.1) for i in range(4)] == [False] * 4
    assert tr.push(base + 0.4) is True
    assert tr.push(base + 0.5) is False  # reset after fire
    tr2 = EscTracker(window=2.0, threshold=5)
    for i in range(4):
        assert tr2.push(base + i * 0.1) is False
    assert tr2.push(base + 10.0) is False  # old hits expired


def test_tilt_debounce_window():
    assert should_suppress_tilt(None, 1.0) is False
    assert should_suppress_tilt(1.0, 1.1) is True
    assert should_suppress_tilt(1.0, 1.5) is False
    assert should_suppress_tilt(1.0, 1.29, window=0.3) is True


# ---- settings/debug ----
def test_debug_log_setting_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "settings.json"
        s = SettingsStore(path=p)
        assert s.settings.debug_log_enabled is False
        s.settings.debug_log_enabled = True
        s.save()
        s2 = SettingsStore(path=p)
        assert s2.settings.debug_log_enabled is True
        assert s2.settings.to_json_dict()["debugLogEnabled"] is True


def test_discovery_debug_file():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "dbg.log"
        log = DiscoveryLog()
        log.set_debug_file(p)
        log.add("hello-phase2")
        assert log.lines() == ["hello-phase2"]
        assert "hello-phase2" in p.read_text(encoding="utf-8")
        log.set_debug_file(None)
        log.add("no-file")
        assert log.lines()[-1] == "no-file"


# ---- hooks compat ----
def test_hooks_touch_filter_compat():
    e = HookEngine()  # old call shape still works
    assert e.should_skip_touch(0xFF515700) is False
    e2 = HookEngine(router=None, touch_filter=lambda extra: is_from_touch(extra))
    assert e2.should_skip_touch(0xFF515700) is True
    assert e2.should_skip_touch(0) is False


# ---- app integration ----
class _DummyHooks:
    def __init__(self):
        self.stops = 0

    def stop(self):
        self.stops += 1


def test_kill_switch_fires_on_five_esc():
    a = _fresh_app()
    dummy = _DummyHooks()
    a.hooks = dummy
    for _ in range(4):
        assert a.route_key(27, True) is False
    assert dummy.stops == 0
    assert a.route_key(27, True) is True
    assert dummy.stops == 1
    assert any("kill-switch" in line for line in a.discovery.lines())


def test_tilt_suppressed_second_pulse():
    a = _fresh_app()
    assert a.store.settings.precise_trigger == "mouseTiltLeft"
    first = a.route_mouse("tiltLeft", True)
    assert first == "precise"
    assert a.route_mouse("tiltLeft", True) == "passthrough"
    a._last_tilt_monotonic = time.monotonic() - 10.0
    assert a.route_mouse("tiltLeft", True) == "precise"


def test_disable_flag_forces_passthrough():
    a = _fresh_app()
    a.store.set_mapping("back", KeyCombo(vk=67, modifiers=KeyCombo.MOD_CTRL))
    assert a.route_mouse("back", True) == "emit"
    fp = appmod.disable_flag_path()
    try:
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("1", encoding="utf-8")
        # fresh instance so TTL cache re-reads the flag
        d2 = tempfile.mkdtemp(prefix="bstbb700_win_phase2b_")
        p2 = pathlib.Path(d2) / "settings.json"
        os.environ["BSTBB700_SETTINGS_PATH"] = str(p2)
        c = appmod.App(store=SettingsStore(path=p2))
        assert c.route_mouse("back", True) == "passthrough"
        assert c.route_key(124, True) is False
        assert "無効化フラグ" in c._hook_status_text()
    finally:
        try:
            if fp.exists():
                fp.unlink()
        except Exception:
            pass


def test_restart_hooks_headless_safe():
    a = _fresh_app()

    class _DummyHooks:
        running = False
        starts = 0

        def start(self):
            self.starts += 1
            self.running = True
            return True

        def stop(self):
            self.running = False

    dummy = _DummyHooks()
    a.hooks = dummy
    a._restart_hooks()
    assert dummy.starts == 1
    assert any("再開" in line for line in a.discovery.lines())


def test_hook_status_text():
    a = _fresh_app()
    assert a._hook_status_text() in ("フック動作中", "フック停止中")
