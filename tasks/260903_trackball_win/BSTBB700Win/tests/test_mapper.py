from core.mapper import decide_action, resolve_tilt, resolve_xbutton


def test_xbutton_default():
    assert resolve_xbutton(1) == "back"
    assert resolve_xbutton(2) == "forward"
    assert resolve_xbutton(1, swap_back_forward=True) == "forward"
    assert resolve_xbutton(2, swap_back_forward=True) == "back"
    assert resolve_xbutton(9) is None


def test_tilt():
    assert resolve_tilt(120) == "tiltRight"
    assert resolve_tilt(-120) == "tiltLeft"
    assert resolve_tilt(0) is None
    assert resolve_tilt(120, tilt_inverted=True) == "tiltLeft"


def test_decide_priority():
    assert decide_action(False, True) == "precise"
    assert decide_action(True, False) == "emit"
    assert decide_action(False, False) == "passthrough"
