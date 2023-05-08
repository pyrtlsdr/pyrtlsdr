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
    with pytest.warns(None) as record:
        import rtlsdr
    assert len(record) == 1
    assert isinstance(record[0].message, rtlsdr.ClientModeWarning)
    assert rtlsdr.RtlSdr is None
    assert rtlsdr.RtlSdrTcpClient is not None
