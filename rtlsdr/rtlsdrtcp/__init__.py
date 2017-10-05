import os

RTLSDR_CLIENT_MODE = False
if os.environ.get('RTLSDR_CLIENT_MODE', '').lower() in ['true', '1', 'yes']:
    RTLSDR_CLIENT_MODE = True

from .client import RtlSdrTcpClient
try:
    from .server import RtlSdrTcpServer
except ImportError:
    if not RTLSDR_CLIENT_MODE:
        raise
