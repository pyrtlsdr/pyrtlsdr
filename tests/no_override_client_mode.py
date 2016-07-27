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
    with pytest.warns(None) as record:
        import rtlsdr
    assert len(record) == 1
    assert isinstance(record[0].message, rtlsdr.ClientModeWarning)
    assert rtlsdr.RtlSdr is None
    assert rtlsdr.RtlSdrTcpClient is not None
