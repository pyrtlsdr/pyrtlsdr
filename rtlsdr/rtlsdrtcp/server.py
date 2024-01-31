#! /usr/bin/env python
import sys
import threading
import struct
import traceback
import argparse

PY2 = sys.version_info[0] == 2
if PY2:
    from SocketServer import TCPServer, BaseRequestHandler
else:
    from socketserver import TCPServer, BaseRequestHandler

from rtlsdr import RtlSdr

from .base import (
    CommunicationError,
    RtlSdrTcpBase,
    ClientMessage,
    ServerMessage,
    AckMessage,
    DEFAULT_READ_SIZE,
    API_METHODS,
    API_DESCRIPTORS,
)

class RtlSdrTcpServer(RtlSdr, RtlSdrTcpBase):

    """Server that connects to a physical dongle to allow client connections.
    """

    def __init__(self, device_index=0, test_mode_enabled=False, serial_number=None,
                 hostname='127.0.0.1', port=None):

        RtlSdrTcpBase.__init__(self, device_index, test_mode_enabled,
                               hostname, port)
        RtlSdr.__init__(self, device_index, test_mode_enabled, serial_number)

    def open(self, device_index=0, test_mode_enabled=False, serial_number=None):
        if not self.device_ready:
            return
        super(RtlSdrTcpServer, self).open(device_index, test_mode_enabled, serial_number)

    def run(self):
        """Runs the server thread and returns.  Use this only if you are
        running mainline code afterwards.
        The server must explicitly be stopped by the stop method before exit.

        """
        if self.server_thread is None:
            self.server_thread = ServerThread(self)
        if self.server_thread.running.is_set():
            return
        self.server_thread.start()
        self.server_thread.running.wait()
        e = self.server_thread.exception
        if e is not None:
            print(self.server_thread.exception_tb)
            raise e
        if self.server_thread.stopped.is_set():
            self.server_thread = None
            self.close()

    def run_forever(self):
        """Runs the server and begins a mainloop.
        The loop will exit with Ctrl-C.
        """
        self.run()
        while True:
            try:
                self.server_thread.stopped.wait(1.)
            except KeyboardInterrupt:
                self.close()
                break

    def close(self):
        """Stops the server (if it's running) and closes the connection to the
        dongle.
        """
        if self.server_thread is not None:
            if self.server_thread.running.is_set():
                self.server_thread.stop()
            self.server_thread = None
        super(RtlSdrTcpServer, self).close()

    def read_bytes(self, num_bytes=DEFAULT_READ_SIZE):
        """Return a packed string of bytes read along with the struct_fmt.
        """
        fmt_str = '%dB' % (num_bytes)
        buffer = super(RtlSdrTcpServer, self).read_bytes(num_bytes)
        s = struct.pack(fmt_str, *buffer)
        return {'struct_fmt':fmt_str, 'data':s}

    def read_samples(self, num_samples=DEFAULT_READ_SIZE):
        """This overrides the base implementation so that the raw data is sent.
        It will be unpacked to I/Q samples on the client side.
        """
        num_samples = 2*num_samples
        return self.read_bytes(num_samples)

class ServerThread(threading.Thread):
    def __init__(self, rtl_sdr):
        super(ServerThread, self).__init__()
        self.rtl_sdr = rtl_sdr
        self.running = threading.Event()
        self.stopped = threading.Event()
        self.exception = None

    def run(self):
        try:
            self.server = Server(self.rtl_sdr)
        except Exception as e:
            self.exception = e
            self.exception_tb = traceback.format_exc()
            self.running.set()
            self.stopped.set()
            return
        rtl_sdr = self.rtl_sdr
        rtl_sdr.device_ready = True
        rtl_sdr.open(rtl_sdr.device_index, rtl_sdr.test_mode_enabled)
        self.running.set()
        self.server.serve_forever()
        self.running.clear()
        rtl_sdr.device_ready = False
        self.stopped.set()

    def stop(self):
        running = getattr(self, 'running', None)
        if running is None or not running.is_set():
            return
        if not hasattr(self, 'server'):
            return
        self.server.shutdown()
        self.server.server_close()
        self.stopped.wait()


class Server(TCPServer):
    REQUEST_RECV_SIZE = 1024

    def __init__(self, rtl_sdr):
        self.rtl_sdr = rtl_sdr
        server_addr = (rtl_sdr.hostname, rtl_sdr.port)
        TCPServer.__init__(self, server_addr, RequestHandler)
        self.handlers = set()

    def server_close(self):
        if not hasattr(self, 'handlers'):
            return
        for h in self.handlers:
            h.close()

class RequestHandler(BaseRequestHandler):
    def setup(self):
        self.finished = False
        self.server.handlers.add(self)

    def handle(self, rx_message=None):
        if rx_message is None:
            rx_message = ClientMessage.from_remote(self.request)
        msg_type = rx_message.header.get('type')
        if msg_type == 'method':
            r = self.handle_method_call(rx_message)
        elif msg_type == 'prop_set':
            r = self.handle_prop_set(rx_message)
        elif msg_type == 'prop_get':
            r = self.handle_prop_get(rx_message)
        else:
            r = False
        if r is False:
            nak = AckMessage(ok=False)
            nak.send_message(self.request)

    def finish(self):
        self.server.handlers.discard(self)

    def close(self):
        self.finished = True

    def handle_method_call(self, rx_message):
        rtl_sdr = self.server.rtl_sdr
        method_name = rx_message.header.get('name')
        arg = rx_message.data
        if method_name not in API_METHODS:
            raise CommunicationError('method %s not allowed' % (method_name))
        try:
            m = getattr(rtl_sdr, method_name)
        except AttributeError:
            msg = 'sdr has no attribute "%s"' % (method_name)
            raise CommunicationError(msg)
        if arg is not None:
            resp = m(arg)
        else:
            resp = m()
        tx_message = ServerMessage(client_message=rx_message, data=resp)
        tx_message.send_message(self.request)

    def handle_prop_set(self, rx_message):
        rtl_sdr = self.server.rtl_sdr
        prop_name = rx_message.header.get('name')
        value = rx_message.data
        if prop_name not in API_DESCRIPTORS:
            raise CommunicationError('property %s not allowed' % (prop_name))
        setattr(rtl_sdr, prop_name, value)
        tx_message = ServerMessage(client_message=rx_message)
        tx_message.send_message(self.request)

    def handle_prop_get(self, rx_message):
        prop_name = rx_message.header.get('name')
        if prop_name not in API_DESCRIPTORS:
            raise CommunicationError('property %s not allowed' % (prop_name))
        rtl_sdr = self.server.rtl_sdr
        value = getattr(rtl_sdr, prop_name)
        tx_message = ServerMessage(client_message=rx_message, data=value)
        tx_message.send_message(self.request)


def run_server():
    """Convenience function to run the server from the command line
    with options for hostname, port and device index.
    """
    p = argparse.ArgumentParser()
    p.add_argument(
        '-a', '--address',
        dest='hostname',
        metavar='address',
        default='127.0.0.1',
        help='Listen address (default is "127.0.0.1")')
    p.add_argument(
        '-p', '--port',
        dest='port',
        type=int,
        default=1235,
        help='Port to listen on (default is 1235)')
    p.add_argument(
        '-d', '--device-index',
        dest='device_index',
        type=int,
        default=0)
    args, remaining = p.parse_known_args()
    o = vars(args)
    server = RtlSdrTcpServer(**o)
    server.run_forever()

if __name__ == '__main__':
    run_server()
