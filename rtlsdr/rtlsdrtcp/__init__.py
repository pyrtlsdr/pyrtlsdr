"""
This module allows client/server communication.

The :class:`~rtlsdr.rtlsdrtcp.server.RtlSdrTcpServer` class is meant to be
connected physically to an SDR dongle and communicate with an instance of
:class:`~rtlsdr.rtlsdrtcp.client.RtlSdrTcpClient`.

The client is intended to function as closely as possible to the base
:class:`~rtlsdr.rtlsdr.RtlSdr` class (as if it had a physical dongle
attached to it).

Both of these classes have the same arguments as the base
:class:`~rtlsdr.rtlsdr.RtlSdr` class with the addition of ``hostname`` and ``port``.

Examples:
    .. code-block:: python

       server = RtlSdrTcpServer(hostname='192.168.1.100', port=12345)
       server.run_forever()
       # Will listen for clients until Ctrl-C is pressed

    .. code-block:: python

       # On another machine (typically)
       client = RtlSdrTcpClient(hostname='192.168.1.100', port=12345)
       client.center_freq = 2e6
       data = client.read_samples()

Note:
    On platforms where the ``librtlsdr`` library cannot be installed/compiled,
    it is possible to import :class:`~rtlsdr.rtlsdrtcp.RtlSdrTcpClient` only by
    setting the environment variable ``"RTLSDR_CLIENT_MODE"`` to ``"true"``.
    If this is set, no other modules will be available.

*Feature added in v0.2.4*
"""

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
