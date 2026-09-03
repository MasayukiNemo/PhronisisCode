from core.keys import plan_strokes
from core.settings import KeyCombo


def test_plan_ctrl_c():
    combo = KeyCombo(vk=67, modifiers=KeyCombo.MOD_CTRL)
    seq = plan_strokes(combo)
    assert seq[0].vk == 162 and seq[0].down is True
    assert seq[1].vk == 67 and seq[1].down is True
    assert seq[-1].down is False
