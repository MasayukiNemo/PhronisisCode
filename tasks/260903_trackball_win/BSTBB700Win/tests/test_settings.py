import tempfile
from pathlib import Path

from core.settings import KeyCombo, SettingsStore


def test_save_load_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "settings.json"
        s = SettingsStore(path=p)
        s.set_mapping("forward", KeyCombo(vk=67, modifiers=KeyCombo.MOD_CTRL))
        s.settings.precise_scale = 0.25
        s.save()
        s2 = SettingsStore(path=p)
        assert s2.mapping_for("forward") is not None
        assert s2.mapping_for("forward").vk == 67
        assert abs(s2.settings.precise_scale - 0.25) < 1e-9


def test_conflict_tilt_left():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "settings.json"
        s = SettingsStore(path=p)
        s.settings.precise_trigger = "mouseTiltLeft"
        s.set_mapping("tiltLeft", KeyCombo(vk=27, modifiers=0))
        assert s.is_precise_trigger_consuming("tiltLeft") is True
        assert s.conflict_message() is not None
        s.set_mapping("tiltLeft", None)
        assert s.conflict_message() is None
