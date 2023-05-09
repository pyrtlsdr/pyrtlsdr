import pytest

@pytest.fixture(autouse=True)
def librtlsdr_override(request):
    """Override the `librtlsdr_override` fixture in conftest.py
    """
    return

@pytest.fixture(params=[True, False])
def librtlsdr_missing(request, monkeypatch):
    class FakeCDLL(object):
        def __init__(self, *args):
            raise Exception()
    if request.param:
        monkeypatch.setattr('ctypes.CDLL', FakeCDLL)
    return request.param

@pytest.mark.no_overrides
def test_dll_loader(librtlsdr_missing):
    if librtlsdr_missing:
        with pytest.raises(ImportError):
            import rtlsdr
            from rtlsdr import rtlsdr
            print(rtlsdr.p_rtlsdr_dev)
    else:
        import rtlsdr
