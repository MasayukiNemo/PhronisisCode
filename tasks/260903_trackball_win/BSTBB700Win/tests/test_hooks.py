from core.hooks import decode_tilt, decode_xbutton, hiword


def test_decode_xbutton():
    assert decode_xbutton(0x00010000) == 1
    assert decode_xbutton(0x00020000) == 2
    assert decode_xbutton(0) is None


def test_hiword_signed():
    assert hiword(120 << 16) == 120
    assert hiword((0xFF88 << 16) & 0xFFFFFFFF) == -120
    assert decode_tilt(120 << 16) == 120
