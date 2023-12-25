import ctypes

import pytest

@pytest.fixture(autouse=True)
def librtlsdr_override(request):
    """Override the `librtlsdr_override` fixture in conftest.py
    """
    return

@pytest.mark.no_overrides
def test_dll_loader():
    import rtlsdr
    assert isinstance(rtlsdr.librtlsdr, ctypes.CDLL)
