"""Win仕上げの回帰テスト。Mac/Win両方で実行可能（Win32呼び出しなし）。"""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import app
from core.settings import KeyCombo, SettingsStore


def _fresh_app():
    d = tempfile.mkdtemp(prefix="bstbb700_win_finish_")
    p = pathlib.Path(d) / "settings.json"
    os.environ["BSTBB700_SETTINGS_PATH"] = str(p)
    return app.App(store=SettingsStore(path=p))


def test_keyboard_f13_toggle_consumes():
    a = _fresh_app()
    a.store.settings.precise_trigger = "f13"
    a.store.settings.precise_mode = "toggle"
    assert a.trigger_vk() == 124
    assert a.route_key(124, True) is True
    assert a.precise.is_active is True
    assert a.route_key(125, True) is False  # other key untouched
    assert a.route_key(124, True) is True
    assert a.precise.is_active is False


def test_keyboard_hold_center_via_custom_vk():
    a = _fresh_app()
    a.store.settings.precise_trigger = "customKey"
    a.store.settings.precise_custom_vk = 36
    a.store.settings.precise_mode = "hold"
    assert a.trigger_vk() == 36
    assert a.route_key(36, True) is True
    assert a.precise.is_active is True
    assert a.route_key(36, False) is True
    assert a.precise.is_active is False


def test_swap_and_tilt_reflected_in_resolve():
    a = _fresh_app()
    assert a.hooks.resolve_mouse_event(0x020B, 0x00010000) == ("back", True)
    a.store.settings.swap_back_forward = True
    assert a.hooks.resolve_mouse_event(0x020B, 0x00010000) == ("forward", True)
    a.store.settings.swap_back_forward = False
    assert a.hooks.resolve_mouse_event(0x020E, 120 << 16) == ("tiltRight", True)
    a.store.settings.tilt_inverted = True
    assert a.hooks.resolve_mouse_event(0x020E, 120 << 16) == ("tiltLeft", True)


def test_custom_vk_roundtrip_and_conflict_refresh():
    a = _fresh_app()
    a.store.settings.precise_trigger = "mouseForward"
    a.store.set_mapping("forward", KeyCombo(vk=67, modifiers=KeyCombo.MOD_CTRL))
    assert a.store.conflict_message() is not None
    assert a.route_mouse("forward", True) == "precise"
    a.store.settings.precise_custom_vk = 125
    a.store.save()
    s2 = SettingsStore(path=a.store.path)
    assert s2.settings.precise_custom_vk == 125
