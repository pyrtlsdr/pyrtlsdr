import sys

collect_ignore = ['setup.py']

ASYNC_AVAILABLE = sys.version_info.major >= 3
if sys.version_info.major == 3:
    ASYNC_AVAILABLE = sys.version_info.minor >= 5
if not ASYNC_AVAILABLE:
    collect_ignore.append('rtlsdr/rtlsdraio.py')
