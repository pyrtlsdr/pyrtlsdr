import sys

import pytest

collect_ignore = ['setup.py', 'demo_waterfall.py']

ASYNC_AVAILABLE = sys.version_info.major >= 3
if sys.version_info.major == 3:
    ASYNC_AVAILABLE = sys.version_info.minor >= 5
if not ASYNC_AVAILABLE:
    collect_ignore.append('test_aio.py')

@pytest.fixture
def sdr_cls():
    from rtlsdr import RtlSdr
    return RtlSdr

@pytest.fixture
def rtlsdrtcp(monkeypatch):
    from rtlsdr import rtlsdrtcp
    return rtlsdrtcp

@pytest.fixture
def rtlsdraio(monkeypatch):
    from rtlsdr import rtlsdraio
    return rtlsdraio
