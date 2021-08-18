import sys
import os

import pytest

def pytest_addoption(parser):
    parser.addoption('--no-overrides', action='store_true',
        help='Run tests that do not override (monkeypatch) librtlsdr')

def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'no_overrides: mark test to not monkeypatch librtlsdr',
    )

def pytest_collection_modifyitems(config, items):
    if config.getoption('--no-overrides'):
        # '--no-overrides' given, don't skip
        return
    skip_no_overrides = pytest.mark.skip(reason='need --no-overrides to run')
    for item in items:
        if 'no_overrides' in item.keywords:
            item.add_marker(skip_no_overrides)

collect_ignore = ['setup.py', 'demo_waterfall.py']

ASYNC_AVAILABLE = sys.version_info.major >= 3
if sys.version_info.major == 3:
    ASYNC_AVAILABLE = sys.version_info.minor >= 5
if not ASYNC_AVAILABLE:
    collect_ignore.append('test_aio.py')

def is_travisci():
    return any([os.environ.get(key) == 'true' for key in ['CI', 'TRAVIS']])

@pytest.fixture(params=[True, False])
def tuner_bandwidth_supported(request, monkeypatch):
    return request.param

@pytest.fixture(params=[True, False])
def tuner_set_bandwidth_supported(request):
    return request.param

@pytest.fixture(autouse=True)
def librtlsdr_override(request,
                       monkeypatch,
                       tuner_bandwidth_supported,
                       tuner_set_bandwidth_supported):

    if isinstance(request.node, pytest.Function):
        # no_override tests will not monkeypatch the wrapper library
        module = request.node.parent
        if 'no_override_' in module.name:
            print('skipping module {}'.format(module))
            return
    monkeypatch.setattr('rtlsdr.rtlsdr.tuner_bandwidth_supported', tuner_bandwidth_supported)
    monkeypatch.setattr('rtlsdr.rtlsdr.tuner_set_bandwidth_supported', 'tuner_set_bandwidth_supported')
    if not is_travisci():
        return
    import testlibrtlsdr
    for attr in ['p_rtlsdr_dev', 'librtlsdr', 'rtlsdr_read_async_cb_t']:
        lib_attr = '.'.join(['rtlsdr', 'rtlsdr', attr])
        override = getattr(testlibrtlsdr, attr)
        monkeypatch.setattr(lib_attr, override)

@pytest.fixture(params=[True, False])
def use_numpy(request, monkeypatch):
    if not request.param:
        monkeypatch.setattr('rtlsdr.rtlsdr.has_numpy', False)
        monkeypatch.setattr('rtlsdr.rtlsdrtcp.base.has_numpy', False)
    return request.param

@pytest.fixture
def sdr_cls():
    from rtlsdr.rtlsdr import RtlSdr
    return RtlSdr

@pytest.fixture
def rtlsdrtcp():
    from rtlsdr import rtlsdrtcp
    return rtlsdrtcp

@pytest.fixture
def rtlsdraio():
    from rtlsdr import rtlsdraio
    return rtlsdraio
