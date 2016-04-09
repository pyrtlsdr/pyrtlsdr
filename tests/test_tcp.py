import time
import socket
import errno

import pytest

def test(rtlsdrtcp, use_numpy):
    from utils import generic_test
    port = 1235
    while True:
        try:
            server = rtlsdrtcp.RtlSdrTcpServer(port=port)
            server.run()
        except socket.error as e:
            if e.errno != errno.EADDRINUSE:
                raise
            server = None
            port += 1
        if server is not None:
            print('server running on port {0}'.format(port))
            break
    client = rtlsdrtcp.RtlSdrTcpClient(port=port)
    try:
        generic_test(client, test_async=False, test_exceptions=False, use_numpy=use_numpy)
        with pytest.raises(NotImplementedError):
            generic_test(client, test_async=True, test_exceptions=False, use_numpy=use_numpy)
    finally:
        server.close()
