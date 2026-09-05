"""Settings store. JSON at %APPDATA%/BSTBB700/settings.json."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class ButtonID(str, Enum):
    BACK = "back"
    FORWARD = "forward"
    CENTER = "center"
    TILT_LEFT = "tiltLeft"
    TILT_RIGHT = "tiltRight"


class PreciseTrigger(str, Enum):
    NONE = "none"
    F13 = "f13"
    F14 = "f14"
    F15 = "f15"
    CAPSLOCK = "capsLock"
    MOUSE_FORWARD = "mouseForward"
    MOUSE_BACK = "mouseBack"
    MOUSE_CENTER = "mouseCenter"
    MOUSE_TILT_RIGHT = "mouseTiltRight"
    MOUSE_TILT_LEFT = "mouseTiltLeft"
    MOUSE_TILT_EITHER = "mouseTiltEither"
    CUSTOM_KEY = "customKey"

    @property
    def display(self) -> str:
        return {
            "none": "なし",
            "f13": "F13キー",
            "f14": "F14キー",
            "f15": "F15キー",
            "capsLock": "CapsLockキー",
            "mouseForward": "進むボタン",
            "mouseBack": "戻るボタン",
            "mouseCenter": "中央ボタン",
            "mouseTiltRight": "チルト右",
            "mouseTiltLeft": "チルト左",
            "mouseTiltEither": "チルト左右どちらも",
            "customKey": "カスタムキー",
        }.get(self.value, self.value)


class PreciseMode(str, Enum):
    TOGGLE = "toggle"
    HOLD = "hold"


@dataclass
class KeyCombo:
    vk: int = 0
    modifiers: int = 0  # bitmask: 1=ctrl 2=shift 4=alt 8=win

    MOD_CTRL = 1
    MOD_SHIFT = 2
    MOD_ALT = 4
    MOD_WIN = 8

    def readable(self) -> str:
        parts = []
        if self.modifiers & self.MOD_CTRL:
            parts.append("Ctrl")
        if self.modifiers & self.MOD_SHIFT:
            parts.append("Shift")
        if self.modifiers & self.MOD_ALT:
            parts.append("Alt")
        if self.modifiers & self.MOD_WIN:
            parts.append("Win")
        parts.append(VK_NAMES.get(self.vk, f"VK{self.vk}"))
        return "+".join(parts)

    def to_dict(self) -> dict:
        return {"vk": self.vk, "modifiers": self.modifiers}

    @staticmethod
    def from_dict(d: dict) -> "KeyCombo":
        return KeyCombo(vk=int(d.get("vk", 0)), modifiers=int(d.get("modifiers", 0)))


VK_NAMES = {
    8: "Backspace", 9: "Tab", 13: "Enter", 19: "Pause", 20: "CapsLock",
    27: "Esc", 32: "Space", 33: "PageUp", 34: "PageDown", 35: "End", 36: "Home",
    37: "Left", 38: "Up", 39: "Right", 40: "Down",
    48: "0", 49: "1", 50: "2", 51: "3", 52: "4", 53: "5", 54: "6", 55: "7", 56: "8", 57: "9",
    65: "A", 66: "B", 67: "C", 68: "D", 69: "E", 70: "F", 71: "G", 72: "H",
    73: "I", 74: "J", 75: "K", 76: "L", 77: "M", 78: "N", 79: "O", 80: "P",
    81: "Q", 82: "R", 83: "S", 84: "T", 85: "U", 86: "V", 87: "W", 88: "X", 89: "Y", 90: "Z",
    112: "F1", 113: "F2", 114: "F3", 115: "F4", 116: "F5", 117: "F6",
    118: "F7", 119: "F8", 120: "F9", 121: "F10", 122: "F11", 123: "F12",
    124: "F13", 125: "F14", 126: "F15", 127: "F16",
    91: "LWin", 92: "RWin", 93: "Apps",
    144: "NumLock", 145: "ScrollLock",
}

TRIGGER_VK = {
    PreciseTrigger.F13: 124,
    PreciseTrigger.F14: 125,
    PreciseTrigger.F15: 126,
    PreciseTrigger.CAPSLOCK: 20,
}


@dataclass
class AppSettings:
    mappings: dict = field(default_factory=dict)  # ButtonID.value -> KeyCombo
    precise_enabled: bool = True
    precise_trigger: str = PreciseTrigger.MOUSE_TILT_LEFT.value
    precise_mode: str = PreciseMode.TOGGLE.value
    precise_scale: float = 0.25
    precise_custom_vk: int = 124
    discovery_enabled: bool = False
    tilt_inverted: bool = False
    swap_back_forward: bool = False
    debug_log_enabled: bool = False
    precise_was_active: bool = False
    normal_speed: int = 10
    hud_enabled: bool = True
    magnifier_enabled: bool = True
    magnifier_zoom: int = 2
    magnifier_size: int = 240

    def to_json_dict(self) -> dict:
        return {
            "mappings": {k: v.to_dict() for k, v in self.mappings.items()},
            "preciseEnabled": self.precise_enabled,
            "preciseTrigger": self.precise_trigger,
            "preciseMode": self.precise_mode,
            "preciseScale": self.precise_scale,
            "preciseCustomVk": self.precise_custom_vk,
            "discoveryEnabled": self.discovery_enabled,
            "tiltInverted": self.tilt_inverted,
            "swapBackForward": self.swap_back_forward,
            "debugLogEnabled": self.debug_log_enabled,
            "preciseWasActive": self.precise_was_active,
            "normalSpeed": self.normal_speed,
            "hudEnabled": self.hud_enabled,
            "magnifierEnabled": self.magnifier_enabled,
            "magnifierZoom": self.magnifier_zoom,
            "magnifierSize": self.magnifier_size,
        }

    @staticmethod
    def from_json_dict(d: dict) -> "AppSettings":
        s = AppSettings()
        raw_map = d.get("mappings", {}) or {}
        out = {}
        for k, v in raw_map.items():
            try:
                out[str(k)] = KeyCombo.from_dict(v)
            except Exception:
                continue
        s.mappings = out
        s.precise_enabled = bool(d.get("preciseEnabled", True))
        s.precise_trigger = str(d.get("preciseTrigger", PreciseTrigger.MOUSE_TILT_LEFT.value))
        s.precise_mode = str(d.get("preciseMode", PreciseMode.TOGGLE.value))
        try:
            s.precise_scale = float(d.get("preciseScale", 0.25))
        except Exception:
            s.precise_scale = 0.25
        s.precise_scale = min(max(s.precise_scale, 0.10), 1.0)
        try:
            s.precise_custom_vk = int(d.get("preciseCustomVk", 124))
        except Exception:
            s.precise_custom_vk = 124
        s.discovery_enabled = bool(d.get("discoveryEnabled", False))
        s.tilt_inverted = bool(d.get("tiltInverted", False))
        s.swap_back_forward = bool(d.get("swapBackForward", False))
        s.debug_log_enabled = bool(d.get("debugLogEnabled", False))
        s.precise_was_active = bool(d.get("preciseWasActive", False))
        try:
            s.normal_speed = int(d.get("normalSpeed", 10))
        except Exception:
            s.normal_speed = 10
        s.normal_speed = min(max(s.normal_speed, 1), 20)
        s.hud_enabled = bool(d.get("hudEnabled", True))
        s.magnifier_enabled = bool(d.get("magnifierEnabled", True))
        try:
            s.magnifier_zoom = int(d.get("magnifierZoom", 2))
        except Exception:
            s.magnifier_zoom = 2
        if s.magnifier_zoom not in (2, 3, 4):
            s.magnifier_zoom = 2
        try:
            s.magnifier_size = int(d.get("magnifierSize", 240))
        except Exception:
            s.magnifier_size = 240
        s.magnifier_size = min(max(s.magnifier_size, 120), 480)
        return s


def default_settings_path() -> Path:
    override = os.environ.get("BSTBB700_SETTINGS_PATH")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "BSTBB700" / "settings.json"
    return Path.home() / ".config" / "BSTBB700" / "settings.json"


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or default_settings_path()
        self.settings = AppSettings()
        self.load()

    def load(self) -> None:
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.settings = AppSettings.from_json_dict(data)
        except Exception:
            self.settings = AppSettings()

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.settings.to_json_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def set_mapping(self, button: str, combo: KeyCombo | None) -> None:
        if combo is None:
            self.settings.mappings.pop(button, None)
        else:
            self.settings.mappings[button] = combo
        self.save()

    def mapping_for(self, button: str) -> KeyCombo | None:
        return self.settings.mappings.get(button)

    def is_precise_trigger_consuming(self, button: str) -> bool:
        if not self.settings.precise_enabled:
            return False
        t = self.settings.precise_trigger
        if t == PreciseTrigger.MOUSE_FORWARD.value and button == ButtonID.FORWARD.value:
            return True
        if t == PreciseTrigger.MOUSE_BACK.value and button == ButtonID.BACK.value:
            return True
        if t == PreciseTrigger.MOUSE_CENTER.value and button == ButtonID.CENTER.value:
            return True
        if t == PreciseTrigger.MOUSE_TILT_RIGHT.value and button == ButtonID.TILT_RIGHT.value:
            return True
        if t == PreciseTrigger.MOUSE_TILT_LEFT.value and button == ButtonID.TILT_LEFT.value:
            return True
        if t == PreciseTrigger.MOUSE_TILT_EITHER.value and button in (
            ButtonID.TILT_LEFT.value,
            ButtonID.TILT_RIGHT.value,
        ):
            return True
        return False

    def conflict_message(self) -> str | None:
        t = self.settings.precise_trigger
        m = self.settings.mappings
        if t == PreciseTrigger.MOUSE_FORWARD.value and ButtonID.FORWARD.value in m:
            return "進むボタンが精密トリガーに使われているため、キー割り当てと排他です。"
        if t == PreciseTrigger.MOUSE_BACK.value and ButtonID.BACK.value in m:
            return "戻るボタンが精密トリガーに使われているため、キー割り当てと排他です。"
        if t == PreciseTrigger.MOUSE_CENTER.value and ButtonID.CENTER.value in m:
            return "中央ボタンが精密トリガーに使われているため、キー割り当てと排他です。"
        if t == PreciseTrigger.MOUSE_TILT_RIGHT.value and ButtonID.TILT_RIGHT.value in m:
            return "チルト右が精密トリガーに使われているため、キー割り当てと排他です。"
        if t == PreciseTrigger.MOUSE_TILT_LEFT.value and ButtonID.TILT_LEFT.value in m:
            return "チルト左が精密トリガーに使われているため、キー割り当てと排他です。"
        if t == PreciseTrigger.MOUSE_TILT_EITHER.value and (
            ButtonID.TILT_LEFT.value in m or ButtonID.TILT_RIGHT.value in m
        ):
            return "チルト左右が精密トリガーに使われているため、キー割り当てと排他です。"
        return None
