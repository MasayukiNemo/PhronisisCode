"""Button mapping resolution. Pure functions for testability."""
from __future__ import annotations

from .settings import ButtonID


def resolve_xbutton(xbutton_id: int, swap_back_forward: bool = False) -> str | None:
    """XBUTTON1=back, XBUTTON2=forward. swap option for reversed devices."""
    back = ButtonID.FORWARD.value if swap_back_forward else ButtonID.BACK.value
    fwd = ButtonID.BACK.value if swap_back_forward else ButtonID.FORWARD.value
    if xbutton_id == 1:
        return back
    if xbutton_id == 2:
        return fwd
    return None


def resolve_tilt(delta: int, tilt_inverted: bool = False) -> str | None:
    """HWHEEL delta sign to tilt direction. delta>0 is right by convention."""
    if delta == 0:
        return None
    right = delta > 0
    if tilt_inverted:
        right = not right
    return ButtonID.TILT_RIGHT.value if right else ButtonID.TILT_LEFT.value


def resolve_mbutton() -> str:
    return ButtonID.CENTER.value


def decide_action(mapping_present: bool, precise_consuming: bool) -> str:
    """Return 'precise' | 'emit' | 'passthrough' in priority order."""
    if precise_consuming:
        return "precise"
    if mapping_present:
        return "emit"
    return "passthrough"
