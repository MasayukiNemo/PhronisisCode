"""Key emission via SendInput. Testable plan builder + Windows executor."""
from __future__ import annotations

from dataclasses import dataclass

from .settings import KeyCombo

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0


@dataclass
class KeyStroke:
    vk: int
    down: bool


def plan_strokes(combo: KeyCombo) -> list[KeyStroke]:
    """Build down/up sequence. Modifiers first down, last up."""
    mods = []
    if combo.modifiers & KeyCombo.MOD_CTRL:
        mods.append(162)  # LCTRL
    if combo.modifiers & KeyCombo.MOD_SHIFT:
        mods.append(160)  # LSHIFT
    if combo.modifiers & KeyCombo.MOD_ALT:
        mods.append(164)  # LALT
    if combo.modifiers & KeyCombo.MOD_WIN:
        mods.append(91)  # LWIN
    seq: list[KeyStroke] = [KeyStroke(vk=m, down=True) for m in mods]
    seq.append(KeyStroke(vk=int(combo.vk), down=True))
    seq.append(KeyStroke(vk=int(combo.vk), down=False))
    for m in reversed(mods):
        seq.append(KeyStroke(vk=m, down=False))
    return seq


def emit(combo: KeyCombo) -> bool:
    """Send keys globally on Windows. Returns False when not on Windows."""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return False
    try:
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.c_void_p)]

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_void_p)]

        class _INPUT_UNION(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]

        assert ctypes.sizeof(INPUT) == 40, ctypes.sizeof(INPUT)

        strokes = plan_strokes(combo)
        n = len(strokes)
        arr = (INPUT * n)()
        try:
            from .winapi import user32
        except ImportError:
            from core.winapi import user32
        for i, s in enumerate(strokes):
            scan = user32.MapVirtualKeyW(int(s.vk), MAPVK_VK_TO_VSC)
            flags = 0 if s.down else KEYEVENTF_KEYUP
            if scan:
                flags |= KEYEVENTF_SCANCODE
            arr[i].type = INPUT_KEYBOARD
            arr[i].u.ki = KEYBDINPUT(wintypes.WORD(int(s.vk)), wintypes.WORD(scan),
                                     wintypes.DWORD(flags), wintypes.DWORD(0), None)
        sent = user32.SendInput(n, arr, ctypes.sizeof(INPUT))
        return int(sent) == n
    except Exception:
        return False
