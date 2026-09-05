"""Precise mode state machine and mouse-speed mapping. Platform independent."""
from __future__ import annotations

import atexit
import signal

from .settings import PreciseMode, PreciseTrigger


def scale_to_speed(saved_speed: int, scale: float) -> int:
    """Map scale 0.10-1.0 to Windows mouse speed 1-20 relative to saved value."""
    s = min(max(float(scale), 0.10), 1.0)
    try:
        base = int(saved_speed)
    except Exception:
        base = 10
    base = min(max(base, 1), 20)
    return min(max(round(base * s), 1), 20)


def is_hold_capable_trigger(trigger: str) -> bool:
    """Tilt has no up event, so hold is impossible. Others support hold."""
    if trigger in (
        PreciseTrigger.MOUSE_TILT_RIGHT.value,
        PreciseTrigger.MOUSE_TILT_LEFT.value,
        PreciseTrigger.MOUSE_TILT_EITHER.value,
    ):
        return False
    return True


class SpeedBackend:
    """Injectable backend. Real backend uses SystemParametersInfo on Windows."""

    def __init__(self):
        self._speed = 10
        self.calls: list = []

    def get(self) -> int:
        return self._speed

    def set(self, v: int) -> None:
        self._speed = int(v)
        self.calls.append(int(v))


class WinSpeedBackend(SpeedBackend):
    SPI_GETMOUSESPEED = 0x0070
    SPI_SETMOUSESPEED = 0x0071
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02

    def get(self) -> int:
        try:
            from .winapi import user32
        except ImportError:
            from core.winapi import user32
        try:
            import ctypes
            v = ctypes.c_int()
            user32.SystemParametersInfoW(self.SPI_GETMOUSESPEED, 0, ctypes.byref(v), 0)
            return int(v.value) or 10
        except Exception:
            return super().get()

    def set(self, v: int) -> None:
        try:
            from .winapi import user32
        except ImportError:
            from core.winapi import user32
        try:
            import ctypes
            user32.SystemParametersInfoW(
                self.SPI_SETMOUSESPEED, 0, ctypes.c_void_p(int(v)),
                self.SPIF_UPDATEINIFILE | self.SPIF_SENDCHANGE,
            )
        except Exception:
            super().set(v)


class PreciseController:
    def __init__(self, backend: SpeedBackend | None = None):
        self.backend = backend or SpeedBackend()
        self.is_active = False
        self.is_hold_pressed = False
        self._saved: int | None = None
        self._applied = False
        self._register_cleanup()

    def _register_cleanup(self) -> None:
        try:
            atexit.register(self.restore)
            for name in ("SIGTERM", "SIGINT"):
                try:
                    sig = getattr(signal, name)
                    prev = signal.getsignal(sig)
                    def _handler(*_a, _p=prev, **_k):
                        try:
                            self.restore()
                        finally:
                            if callable(_p):
                                try:
                                    _p(*_a, **_k)
                                except Exception:
                                    pass
                    signal.signal(sig, _handler)
                except Exception:
                    pass
        except Exception:
            pass

    def rescale(self, scale: float) -> None:
        if not self.is_active:
            return
        if self._saved is None:
            try:
                self._saved = int(self.backend.get())
            except Exception:
                self._saved = 10
        self.backend.set(scale_to_speed(self._saved, scale))
        self._applied = True

    @property
    def is_applied(self) -> bool:
        return self._applied

    def _apply(self, scale: float) -> None:
        if self._saved is None:
            try:
                self._saved = int(self.backend.get())
            except Exception:
                self._saved = 10
        self.backend.set(scale_to_speed(self._saved, scale))
        self._applied = True

    def restore(self) -> None:
        if not self._applied:
            return
        try:
            if self._saved is not None:
                self.backend.set(int(self._saved))
        finally:
            self._applied = False

    def set_active(self, active: bool, scale: float) -> None:
        if active == self.is_active and active == self._applied:
            return
        self.is_active = bool(active)
        if self.is_active:
            self._apply(scale)
        else:
            self.restore()

    def toggle(self, scale: float, enabled: bool = True, mode: str = "toggle") -> bool:
        if not enabled or mode != PreciseMode.TOGGLE.value:
            return False
        self.set_active(not self.is_active, scale)
        return True

    def hold_began(self, scale: float, enabled: bool = True, mode: str = "hold") -> bool:
        if not enabled or mode != PreciseMode.HOLD.value:
            return False
        self.is_hold_pressed = True
        self.set_active(True, scale)
        return True

    def hold_ended(self, mode: str = "hold") -> bool:
        if mode != PreciseMode.HOLD.value:
            return False
        self.is_hold_pressed = False
        self.set_active(False, 1.0)
        return True

    def handle_mouse_trigger(self, button: str, is_down: bool, trigger: str,
                             mode: str, scale: float, enabled: bool = True) -> bool:
        if not enabled:
            return False
        from .settings import ButtonID
        mapping = {
            PreciseTrigger.MOUSE_FORWARD.value: [ButtonID.FORWARD.value],
            PreciseTrigger.MOUSE_CENTER.value: [ButtonID.CENTER.value],
            PreciseTrigger.MOUSE_TILT_RIGHT.value: [ButtonID.TILT_RIGHT.value],
            PreciseTrigger.MOUSE_TILT_LEFT.value: [ButtonID.TILT_LEFT.value],
            PreciseTrigger.MOUSE_TILT_EITHER.value: [ButtonID.TILT_LEFT.value, ButtonID.TILT_RIGHT.value],
        }
        if button not in mapping.get(trigger, []):
            return False
        # Tilt forced toggle even in hold mode (no up event)
        if button in (ButtonID.TILT_LEFT.value, ButtonID.TILT_RIGHT.value) and mode == PreciseMode.HOLD.value:
            if is_down:
                self.set_active(not self.is_active, scale)
            return True
        if mode == PreciseMode.TOGGLE.value:
            if is_down:
                self.toggle(scale, enabled, mode)
            return True
        if is_down:
            self.hold_began(scale, enabled, mode)
        else:
            self.hold_ended(mode)
        return True
