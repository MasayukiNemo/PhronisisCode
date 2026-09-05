import os

from core.keys import emit, plan_strokes
from core.settings import KeyCombo


def test_plan_ctrl_c():
    combo = KeyCombo(vk=67, modifiers=KeyCombo.MOD_CTRL)
    seq = plan_strokes(combo)
    assert seq[0].vk == 162 and seq[0].down is True
    assert seq[1].vk == 67 and seq[1].down is True
    assert seq[-1].down is False


def test_emit_f24_live_windows_only():
    """SendInput struct size guard: fails with 87 when INPUT != 40 bytes."""
    if os.name != "nt":
        return
    assert emit(KeyCombo(vk=135, modifiers=0)) is True
