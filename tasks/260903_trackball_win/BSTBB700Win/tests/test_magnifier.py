"""Magnifier tests. Geometry pure + headless controller. No windows opened."""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import app as appmod
from core.magnifier import (DEFAULT_SIZE, DEFAULT_ZOOM, MAG_INTERVAL_MS,
                            MagnifierController, compute_layout)
from core.settings import SettingsStore


def _fresh_app():
    d = tempfile.mkdtemp(prefix="bstbb700_win_mag_")
    p = pathlib.Path(d) / "settings.json"
    os.environ["BSTBB700_SETTINGS_PATH"] = str(p)
    return appmod.App(store=SettingsStore(path=p))


def test_layout_center():
    lay = compute_layout(960, 540, 320, 2, 1920, 1080)
    assert lay["size"] == 320
    assert lay["src"] == 160
    assert lay["wx"] == 960 + 24
    assert lay["wy"] == 540 - 24 - 320
    assert lay["sx"] == 960 - 80
    assert lay["sy"] == 540 - 80


def test_layout_clamped_corners():
    lay = compute_layout(10, 10, 320, 2, 1920, 1080)
    assert lay["wx"] >= 0 and lay["wy"] >= 0
    assert lay["sx"] >= 0 and lay["sy"] >= 0
    lay = compute_layout(1910, 1070, 320, 4, 1920, 1080)
    assert lay["wx"] + lay["size"] <= 1920
    assert lay["wy"] + lay["size"] <= 1080
    assert lay["src"] == 80
    assert lay["sx"] + lay["src"] <= 1920
    assert lay["sy"] + lay["src"] <= 1080


def test_settings_roundtrip_magnifier():
    a = _fresh_app()
    a.store.settings.magnifier_enabled = False
    a.store.settings.magnifier_zoom = 4
    a.store.settings.magnifier_size = 480
    a.store.save()
    b = SettingsStore(path=a.store.path)
    assert b.settings.magnifier_enabled is False
    assert b.settings.magnifier_zoom == 4
    assert b.settings.magnifier_size == 480
    a.store.settings.magnifier_zoom = 99
    from core.settings import AppSettings

    s = AppSettings.from_json_dict(a.store.settings.to_json_dict())
    assert s.magnifier_zoom == 2  # invalid falls back


def test_controller_headless_noop():
    c = MagnifierController(settings_provider=lambda: None)
    assert c.tick(None, True) is False
    assert c.visible is False


def test_setters_clamp():
    a = _fresh_app()
    a._set_magnifier_zoom("3倍")
    assert a.store.settings.magnifier_zoom == 3
    a._set_magnifier_zoom("9倍")
    assert a.store.settings.magnifier_zoom == 3
    a._set_magnifier_size(1000)
    assert a.store.settings.magnifier_size == 480
    a._set_magnifier_size(50)
    assert a.store.settings.magnifier_size == 120
    assert MAG_INTERVAL_MS == 100
    assert DEFAULT_SIZE == 240 and DEFAULT_ZOOM == 2


def test_layout_virtual_origin():
    lay = compute_layout(-1900, 500, 240, 2, 3840, 1080, org_x=-1920, org_y=0)
    assert lay["wx"] >= -1920
    assert lay["wx"] + lay["size"] <= 1920
    assert lay["sx"] >= -1920
    assert lay["sx"] + lay["src"] <= 1920


def test_virtual_screen_returns_tuple():
    from core.magnifier import virtual_screen

    vs = virtual_screen()
    assert len(vs) == 4
    assert vs[2] >= 0 and vs[3] >= 0
