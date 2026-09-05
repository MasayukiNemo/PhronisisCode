"""Phase1 tests. Mac-runnable, no mainloop (unit only)."""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import app
from core.autostart import exe_path, is_enabled, is_frozen, set_enabled
from core.settings import KeyCombo, SettingsStore
from core.vktable import PRESETS, VK_ENTRIES, label_for, modifier_bits


def _fresh_app():
    d = tempfile.mkdtemp(prefix="bstbb700_win_phase1_")
    p = pathlib.Path(d) / "settings.json"
    os.environ["BSTBB700_SETTINGS_PATH"] = str(p)
    return app.App(store=SettingsStore(path=p))


def test_preset_vks_exist_in_table():
    assert len(VK_ENTRIES) >= 70
    assert len(PRESETS) == 15
    vks = {vk for vk, _label, _group in VK_ENTRIES}
    for name, vk, _mods in PRESETS:
        if vk is None:
            continue
        assert vk in vks, name


def test_label_for():
    assert label_for(67) == "C"
    assert label_for(124) == "F13"
    assert label_for(9) == "Tab"
    assert label_for(9999) == "VK9999"


def test_autostart_mac_noop():
    assert is_frozen() is False
    assert exe_path() is None
    assert is_enabled() is False
    ok, msg = set_enabled(True)
    assert ok is False
    assert isinstance(msg, str) and msg
    ok, msg = set_enabled(False)
    assert ok is False
    assert isinstance(msg, str) and msg


def test_modifier_bits_pure():
    assert modifier_bits({}) == 0
    assert modifier_bits({"ctrl": True}) == KeyCombo.MOD_CTRL
    assert modifier_bits({"shift": True}) == KeyCombo.MOD_SHIFT
    assert modifier_bits({"alt": True}) == KeyCombo.MOD_ALT
    assert modifier_bits({"win": True}) == KeyCombo.MOD_WIN
    assert modifier_bits({"ctrl": True, "shift": True}) == (
        KeyCombo.MOD_CTRL | KeyCombo.MOD_SHIFT
    )


def test_preset_keycombo_roundtrip():
    for _name, vk, mods in PRESETS:
        if vk is None:
            continue
        combo = KeyCombo(vk=vk, modifiers=mods)
        assert combo.readable()
        back = KeyCombo.from_dict(combo.to_dict())
        assert back.vk == vk and back.modifiers == mods


def test_capture_records_and_consumes():
    a = _fresh_app()
    a._capturing = {"kind": "map", "button": "back"}
    assert a.route_key(67, True) is True
    assert a._capturing is None
    cur = a.store.mapping_for("back")
    assert cur is not None and cur.vk == 67


def test_capture_keyup_consumed_without_record():
    a = _fresh_app()
    a._capturing = {"kind": "map", "button": "back"}
    assert a.route_key(67, False) is True
    assert a._capturing is not None
    assert a.store.mapping_for("back") is None


def test_capture_esc_cancels():
    a = _fresh_app()
    a._capturing = {"kind": "map", "button": "back"}
    assert a.route_key(27, True) is True
    assert a._capturing is None
    assert a._capture_result is None
    assert a.store.mapping_for("back") is None


def test_cancel_after_record_keeps_result():
    a = _fresh_app()
    a._capturing = {"kind": "map", "button": "back"}
    assert a.route_key(13, True) is True  # Enter recorded
    assert a._capturing is None
    a._cancel_capture()  # stray Cancel activation must not wipe Enter
    cur = a.store.mapping_for("back")
    assert cur is not None and cur.vk == 13


def test_cancel_while_capturing_clears():
    a = _fresh_app()
    a._capturing = {"kind": "map", "button": "back"}
    a._cancel_capture()
    assert a._capturing is None
    assert a._capture_result is None
    assert a.store.mapping_for("back") is None


def test_capture_modifier_waits_for_combo():
    a = _fresh_app()
    a._capturing = {"kind": "map", "button": "back"}
    assert a.route_key(162, True) is True  # Ctrl down alone: swallowed, keep capturing
    assert a._capturing is not None
    assert a.store.mapping_for("back") is None
    assert a.route_key(67, True) is True  # C with (mocked-off) live mods
    cur = a.store.mapping_for("back")
    assert cur is not None and cur.vk == 67


def test_capture_custom_sets_trigger():
    a = _fresh_app()
    a._capturing = {"kind": "custom", "button": None}
    assert a.route_key(65, True) is True
    assert a._capturing is None
    assert a.store.settings.precise_custom_vk == 65
    assert a.store.settings.precise_trigger == "customKey"


def test_existing_behavior_preserved():
    a = _fresh_app()
    assert a.trigger_vk() is None  # default trigger is mouse tilt
    assert a.route_mouse("back", True) == "passthrough"
    assert a.route_key(124, True) is False  # no keyboard trigger by default
    a.store.set_mapping("back", KeyCombo(vk=67, modifiers=KeyCombo.MOD_CTRL))
    assert a.route_mouse("back", True) == "emit"
    a.store.settings.precise_trigger = "f13"
    a.store.settings.precise_mode = "toggle"
    assert a.trigger_vk() == 124
    assert a.route_key(124, True) is True
    assert a.route_key(125, True) is False


class _DummyDialog:
    def __init__(self):
        self.released = False
        self.destroyed = False

    def grab_release(self):
        self.released = True

    def destroy(self):
        self.destroyed = True


def test_cancel_closes_dialog_immediately():
    a = _fresh_app()
    dlg = _DummyDialog()
    a._capture_dialog = dlg
    a._capturing = {"kind": "map", "button": "back"}
    a._cancel_capture()
    assert a._capturing is None
    assert a._capture_dialog is None
    assert dlg.released is True and dlg.destroyed is True


def test_start_capture_replaces_existing_dialog():
    a = _fresh_app()
    old = _DummyDialog()
    a._capture_dialog = old
    a._start_capture("map", "back")  # headless: root is None
    assert a._capturing == {"kind": "map", "button": "back"}
    assert old.released is True and old.destroyed is True
    assert a._capture_dialog is None


def test_reset_reports_outcome_headless():
    a = _fresh_app()
    a.store.set_mapping("back", KeyCombo(vk=67, modifiers=KeyCombo.MOD_CTRL))

    class _Var:
        def __init__(self):
            self.v = ""

        def set(self, v):
            self.v = v

        def get(self):
            return self.v

    a._general_msg = _Var()
    a._reset_settings()
    assert a.store.mapping_for("back") is None
    assert a._general_msg.get() == "設定をリセットした"
    assert a.precise.is_active is False
