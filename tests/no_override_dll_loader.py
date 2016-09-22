import pytest

no_overrides = pytest.mark.skipif(
    not pytest.config.getoption('--no-overrides'),
    reason='need --no-overrides to run'
)

@pytest.fixture(params=[True, False])
def librtlsdr_missing(request, monkeypatch):
    class FakeCDLL(object):
        def __init__(self, *args):
            raise Exception()
    if request.param:
        monkeypatch.setattr('ctypes.CDLL', FakeCDLL)
    return request.param

@no_overrides
def test_dll_loader(librtlsdr_missing):
    if librtlsdr_missing:
        with pytest.raises(ImportError):
            import rtlsdr
            from rtlsdr import rtlsdr
            print(rtlsdr.p_rtlsdr_dev)
    else:
        import rtlsdr
