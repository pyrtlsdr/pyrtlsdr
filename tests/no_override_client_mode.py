import pytest

@pytest.fixture
def client_mode(monkeypatch):
    monkeypatch.setenv('RTLSDR_CLIENT_MODE', 'true')

def test_client_mode(client_mode):
    import rtlsdr
    assert rtlsdr.RtlSdr is None
    assert rtlsdr.RtlSdrTcpClient is not None
