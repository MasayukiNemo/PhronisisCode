from core.precise import PreciseController, SpeedBackend, is_hold_capable_trigger, scale_to_speed


def test_scale_mapping():
    assert scale_to_speed(10, 0.25) == 2 or scale_to_speed(10, 0.25) == 3
    assert scale_to_speed(10, 1.0) == 10
    assert scale_to_speed(10, 0.10) == 1
    assert scale_to_speed(20, 1.0) == 20


def test_toggle():
    b = SpeedBackend()
    c = PreciseController(backend=b)
    assert c.is_active is False
    c.toggle(0.25, enabled=True, mode="toggle")
    assert c.is_active is True
    assert c.is_applied is True
    c.toggle(0.25, enabled=True, mode="toggle")
    assert c.is_active is False


def test_hold_center():
    b = SpeedBackend()
    c = PreciseController(backend=b)
    assert c.handle_mouse_trigger("center", True, "mouseCenter", "hold", 0.25, True) is True
    assert c.is_active is True
    assert c.handle_mouse_trigger("center", False, "mouseCenter", "hold", 0.25, True) is True
    assert c.is_active is False


def test_tilt_forced_toggle_in_hold():
    b = SpeedBackend()
    c = PreciseController(backend=b)
    assert c.handle_mouse_trigger("tiltLeft", True, "mouseTiltLeft", "hold", 0.25, True) is True
    assert c.is_active is True

    assert is_hold_capable_trigger("mouseTiltLeft") is False
    assert is_hold_capable_trigger("mouseCenter") is True
    assert is_hold_capable_trigger("mouseForward") is True


def test_restore():
    b = SpeedBackend()
    b._speed = 10
    c = PreciseController(backend=b)
    c.set_active(True, 0.25)
    assert b.get() != 10
    c.restore()
    assert b.get() == 10
