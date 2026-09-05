"""VK table and presets. Pure data, Mac-importable (no win32 calls)."""
from __future__ import annotations

try:
    from core.settings import KeyCombo
except ImportError:  # `python -m BSTBB700Win.app` package mode
    from .settings import KeyCombo

# (vk, label, group)
VK_ENTRIES: list[tuple[int, str, str]] = [
    *((vk, chr(vk), "文字") for vk in range(65, 91)),  # A-Z
    *((vk, chr(vk), "数字") for vk in range(48, 58)),  # 0-9
    *((vk, f"F{vk - 111}", "ファンクション") for vk in range(112, 136)),  # F1-F24
    (37, "Left", "方向"),
    (38, "Up", "方向"),
    (39, "Right", "方向"),
    (40, "Down", "方向"),
    (8, "Backspace", "編集"),
    (9, "Tab", "編集"),
    (13, "Enter", "編集"),
    (27, "Esc", "編集"),
    (32, "Space", "編集"),
    (33, "PageUp", "編集"),
    (34, "PageDown", "編集"),
    (35, "End", "編集"),
    (36, "Home", "編集"),
    (45, "Insert", "編集"),
    (46, "Delete", "編集"),
    (20, "CapsLock", "その他"),
    (19, "Pause", "その他"),
    (91, "LWin", "その他"),
    (92, "RWin", "その他"),
    (93, "Apps", "その他"),
    (144, "NumLock", "その他"),
    (145, "ScrollLock", "その他"),
]

# (name, vk or None, mods). None = unassigned.
PRESETS: list[tuple[str, int | None, int]] = [
    ("未割り当て", None, 0),
    ("戻る (Alt+Left)", 37, KeyCombo.MOD_ALT),
    ("進む (Alt+Right)", 39, KeyCombo.MOD_ALT),
    ("コピー (Ctrl+C)", 67, KeyCombo.MOD_CTRL),
    ("ペースト (Ctrl+V)", 86, KeyCombo.MOD_CTRL),
    ("カット (Ctrl+X)", 88, KeyCombo.MOD_CTRL),
    ("取り消し (Ctrl+Z)", 90, KeyCombo.MOD_CTRL),
    ("やり直し (Ctrl+Y)", 89, KeyCombo.MOD_CTRL),
    ("全選択 (Ctrl+A)", 65, KeyCombo.MOD_CTRL),
    ("検索 (Ctrl+F)", 70, KeyCombo.MOD_CTRL),
    ("タブ次 (Ctrl+Tab)", 9, KeyCombo.MOD_CTRL),
    ("タブ前 (Ctrl+Shift+Tab)", 9, KeyCombo.MOD_CTRL | KeyCombo.MOD_SHIFT),
    ("F13", 124, 0),
    ("F14", 125, 0),
    ("F15", 126, 0),
]

# Modifier VKs recorded as the key itself (no extra modifier bits).
MODIFIER_VKS = frozenset({160, 161, 162, 163, 164, 165, 91, 92})


def label_for(vk: int) -> str:
    for v, label, _group in VK_ENTRIES:
        if v == int(vk):
            return label
    return f"VK{vk}"


def modifier_bits(state: dict) -> int:
    """Pure part of capture modifier detection: {"ctrl","shift","alt","win"} -> bitmask."""
    bits = 0
    try:
        if state.get("ctrl"):
            bits |= KeyCombo.MOD_CTRL
        if state.get("shift"):
            bits |= KeyCombo.MOD_SHIFT
        if state.get("alt"):
            bits |= KeyCombo.MOD_ALT
        if state.get("win"):
            bits |= KeyCombo.MOD_WIN
    except Exception:
        pass
    return bits
