import pytest

no_overrides = pytest.mark.skipif(
    not pytest.config.getoption('--no-overrides'),
    reason='need --no-overrides to run'
)

@pytest.fixture
def client_mode(monkeypatch):
    monkeypatch.setenv('RTLSDR_CLIENT_MODE', 'true')

@no_overrides
def test_client_mode(client_mode):
    import rtlsdr
    assert rtlsdr.RtlSdr is None
    assert rtlsdr.RtlSdrTcpClient is not None
