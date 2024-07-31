import pytest

@pytest.fixture(autouse=True)
def librtlsdr_override(request):
    """Override the `librtlsdr_override` fixture in conftest.py
    """
    return

@pytest.fixture
def client_mode(monkeypatch):
    monkeypatch.setenv('RTLSDR_CLIENT_MODE', 'true')

@pytest.mark.no_overrides
def test_client_mode(client_mode):
    with pytest.warns(Warning) as record:
        import rtlsdr
    assert len(record) >= 1
    warn_classes = [rec.message.__class__ for rec in record]
    assert rtlsdr.ClientModeWarning in warn_classes
    assert rtlsdr.RtlSdr is None
    assert rtlsdr.RtlSdrTcpClient is not None
