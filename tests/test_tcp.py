import time
import socket

def test(rtlsdrtcp):
    from utils import generic_test
    print(rtlsdrtcp.RtlSdr)
    #assert rtlsdrtcp.RtlSdrTcpBase.__bases__[0] is rtlsdrtcp.RtlSdr
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
        generic_test(client)
    finally:
        server.close()
