#! /usr/bin/env python

import sys
import time
import threading
import select
import socket
import struct
import errno
import argparse
import traceback
import json

PY2 = sys.version_info[0] == 2
if PY2:
    from SocketServer import TCPServer, BaseRequestHandler
else:
    from socketserver import TCPServer, BaseRequestHandler

try:
    from rtlsdr import RtlSdr
except ImportError:
    from .rtlsdr import RtlSdr


MAX_BUFFER_SIZE = 4096
RECEIVE_TIMEOUT = 20


class CommunicationError(Exception):
    def __init__(self, msg, source_exc=None):
        self.msg = msg
        self.source_exc = source_exc

    def __str__(self):
        s = self.msg
        if self.source_exc is not None:
            s = 'SOURCE EXCEPTION:\n%s\n\n%s' % (traceback.format_exc(), s)
        return s


class RtlSdrTcpBase(RtlSdr):
    # Use port 1235 as default since rtl_tcp uses 1234
    DEFAULT_PORT = 1235

    def __init__(self, device_index=0, test_mode_enabled=False,
                 hostname='127.0.0.1', port=None):
        self.device_index = device_index
        self.test_mode_enabled = test_mode_enabled
        self.hostname = hostname
        self.port = port
        if self.port is None:
            self.port = self.DEFAULT_PORT
        self.device_ready = False
        self.server_thread = None
        super(RtlSdrTcpBase, self).__init__(device_index, test_mode_enabled)


class RtlSdrTcpServer(RtlSdrTcpBase):

    """Server that connects to a physical dongle to allow client connections.
    """

    def open(self, device_index=0, test_mode_enabled=False):
        if not self.device_ready:
            return
        super(RtlSdrTcpServer, self).open(device_index, test_mode_enabled)

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

    def read_bytes(self, num_bytes=RtlSdr.DEFAULT_READ_SIZE):
        """Return a packed string of bytes read along with the struct_fmt.
        """
        fmt_str = '%dB' % (num_bytes)
        buffer = super(RtlSdrTcpServer, self).read_bytes(num_bytes)
        s = struct.pack(fmt_str, *buffer)
        return {'struct_fmt':fmt_str, 'data':s}

    def read_samples(self, num_samples=RtlSdr.DEFAULT_READ_SIZE):
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


API_METHODS = (
    'get_center_freq', 'set_center_freq',
    'get_sample_rate', 'set_sample_rate',
    'get_gain', 'set_gain',
    'get_freq_correction', 'set_freq_correction',
    'get_gains',
    'get_tuner_type',
    'set_direct_sampling',
    'read_bytes',
    'read_samples',
)
API_DESCRIPTORS = {
    'center_freq', 'fc',
    'sample_rate', 'rs',
    'gain',
    'freq_correction',
}


class MessageBase(object):

    """Base class for messages sent between clients and servers.

    Hanldes serialization/deserialization and communication with
    socket type objects.

    """

    def __init__(self, **kwargs):
        self.timestamp = kwargs.get('timestamp')
        self.header = self.get_header(**kwargs)
        self.data = self.get_data(**kwargs)

    @staticmethod
    def _send(sock, data):
        if not PY2 and isinstance(data, str):
            data = data.encode()
        r, w, e = select.select([], [sock], [], .5)
        if sock not in w:
            raise CommunicationError('socket %r not ready for write' % (sock))
        return sock.send(data)

    @staticmethod
    def _recv(sock):
        start_ts = time.time()
        r, w, e = select.select([sock], [], [], RECEIVE_TIMEOUT)
        if not len(r):
            now = time.time()
            raise CommunicationError('No response from peer after %s seconds' % (now - start_ts))
        if sock not in r:
            raise CommunicationError('socket %r not ready for read' % (sock))
        return sock.recv(MAX_BUFFER_SIZE)

    @classmethod
    def from_remote(cls, sock):
        """Reads data for the socket buffer and reconstructs the appropriate
        message that was sent by the other end.
        """
        header = cls._recv(sock)
        if not PY2:
            header = header.decode()
        kwargs = json.loads(header)
        if kwargs.get('ACK'):
            cls = AckMessage
        return cls(**kwargs)

    def get_header(self, **kwargs):
        d = {}
        ts = kwargs.get('timestamp')
        if ts is None:
            ts = time.time()
        d['timestamp'] = ts
        return d

    def get_data(self, **kwargs):
        return kwargs.get('data', kwargs.get('header', {}).get('data'))

    def send_message(self, sock):
        header, data = self._serialize()
        self._send(sock, header)

    def get_response(self, sock):
        cls = self.get_response_class()
        return cls.from_remote(sock)

    def get_ack_response(self, sock):
        return AckMessage.from_remote(sock)

    def _serialize(self):
        struct_fmt = self.header.get('struct_fmt')
        if struct_fmt is not None:
            return json.dumps(self.header), self.data
        data = self.header.copy()
        data.setdefault('data', self.data)
        return json.dumps(data), None



class AckMessage(MessageBase):

    """Simple message type meant for ACKnolegemnt of message receipt."""

    def get_header(self, **kwargs):
        d = super(AckMessage, self).get_header(**kwargs)
        d['ACK'] = True
        d['ok'] = kwargs.get('ok', True)
        return d


class ServerMessage(MessageBase):

    @classmethod
    def from_remote(cls, sock):
        """Reads data for the socket buffer and reconstructs the appropriate
        message that was sent by the other end.

        This method is used by clients to reconstruct ServerMessage objects
        and if necessary, use multiple read calls to get the entire message
        (if the message size is greater than the buffer length)

        """
        header = cls._recv(sock)
        if not PY2:
            header = header.decode()
        kwargs = json.loads(header)
        struct_fmt = kwargs.get('struct_fmt')
        if struct_fmt is not None:
            data_len = struct.calcsize(struct_fmt)
        else:
            return cls(**kwargs)
        ack_msg = AckMessage()
        ack_msg.send_message(sock)
        recv = None
        while data_len > 0:
            _recv = cls._recv(sock)
            if recv is None:
                recv = _recv
            else:
                recv += _recv
            data_len -= len(_recv)
        kwargs['data'] = struct.unpack(struct_fmt, recv)
        return cls(**kwargs)

    def send_message(self, sock):
        """Sends the message data to clients.

        If necessary, uses multiple calls to send to ensure all data has
        actually been sent through the socket objects's buffer.

        """
        header, data = self._serialize()

        self._send(sock, header)
        if isinstance(self.data, dict):
            struct_fmt = self.data.get('struct_fmt')
        else:
            struct_fmt = None
        if struct_fmt is not None:
            data = self.data['data']
            data_len = struct.calcsize(struct_fmt)
            ack = self.get_ack_response(sock)
            if not ack.header.get('ok'):
                raise CommunicationError('No ACK received')
            while data_len > 0:
                sent = self._send(sock, data)
                data_len -= sent
                data = data[sent:]

    def get_header(self, **kwargs):
        d = super(ServerMessage, self).get_header(**kwargs)
        d['success'] = kwargs.get('success', True)
        client_message = kwargs.get('client_message')
        if client_message is not None:
            d['request'] = client_message.header
        else:
            d['request'] = kwargs.get('request')
        return d

    def get_data(self, **kwargs):
        d = super(ServerMessage, self).get_data(**kwargs)
        if isinstance(d, dict) and 'struct_fmt' in d:
            self.header['struct_fmt'] = d['struct_fmt']
        return d

    def get_response_class(self):
        return AckMessage


class ClientMessage(MessageBase):
    def send_message(self, sock):
        super(ClientMessage, self).send_message(sock)
        return self.get_response(sock)

    def get_header(self, **kwargs):
        d = super(ClientMessage, self).get_header(**kwargs)
        keys = ['type', 'name']
        d.update({k: kwargs.get(k) for k in keys})
        return d

    def get_response_class(self):
        return ServerMessage


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


class RtlSdrTcpClient(RtlSdrTcpBase):

    """Client object that connects to a remote server.

    Exposes most of the methods and descriptors that are available in the
    RtlSdr class in a transparent manner allowing an interface that is nearly
    identical to the core API.

    """

    def open(self, *args):
        self._socket = None
        self._keep_alive = False
        self.device_opened = True

    def close(self):
        self.device_opened = False

    def _build_socket(self):
        s = getattr(self, '_socket', None)
        if s is None:
            s = self._socket = socket.socket(socket.AF_INET,
                                             socket.SOCK_STREAM)
            s.connect((self.hostname, self.port))
        return s

    def _close_socket(self):
        if self._keep_alive:
            return
        s = getattr(self, '_socket', None)
        if s is None:
            return
        print('client closing socket')
        s.close()
        self._socket = None

    def _communicate(self, tx_message):
        s = self._build_socket()
        resp = tx_message.send_message(s)
        if isinstance(resp, ServerMessage):
            if not resp.header.get('success'):
                msg = 'server was unsuccessful. msg=%s' % (tx_message.header)
                raise CommunicationError(msg)
            resp_data = resp.data
        elif isinstance(resp, AckMessage):
            if not resp.header.get('ok'):
                raise CommunicationError('ACK message recieved as "NAK"')
            resp_data = None
        self._close_socket()
        return resp_data

    def _communicate_method(self, method_name, arg=None):
        msg = ClientMessage(type='method', name=method_name, data=arg)
        return self._communicate(msg)

    def _communicate_descriptor_get(self, prop_name):
        msg = ClientMessage(type='prop_get', name=prop_name)
        return self._communicate(msg)

    def _communicate_descriptor_set(self, prop_name, value):
        msg = ClientMessage(type='prop_set', name=prop_name, data=value)
        return self._communicate(msg)

    def get_center_freq(self):
        return self._communicate_descriptor_get('fc')

    def set_center_freq(self, value):
        self._communicate_descriptor_set('fc', value)

    def get_sample_rate(self):
        return self._communicate_descriptor_get('rs')

    def set_sample_rate(self, value):
        self._communicate_descriptor_set('rs', value)

    def get_gain(self):
        return self._communicate_descriptor_get('gain')

    def set_gain(self, value):
        self._communicate_descriptor_set('gain', value)

    def get_freq_correction(self):
        return self._communicate_descriptor_get('freq_correction')

    def set_freq_correction(self, value):
        self._communicate_descriptor_set('freq_correction', value)

    def get_gains(self):
        return self._communicate_method('get_gains')

    def get_tuner_type(self):
        return self._communicate_method('get_tuner_type')

    def set_direct_sampling(self, value):
        self._communicate_method('set_direct_sampling', value)

    def read_bytes(self, num_bytes=RtlSdr.DEFAULT_READ_SIZE):
        return self._communicate_method('read_bytes', num_bytes)

    def read_samples(self, num_samples=RtlSdr.DEFAULT_READ_SIZE):
        raw_data = self._communicate_method('read_samples', num_samples)
        iq = self.packed_bytes_to_iq(raw_data)
        return iq

    def read_bytes_async(self, *args):
        raise NotImplementedError('Async read not available in TCP mode')

    center_freq = fc = property(get_center_freq, set_center_freq)
    sample_rate = rs = property(get_sample_rate, set_sample_rate)
    gain = property(get_gain, set_gain)
    freq_correction = property(get_freq_correction, set_freq_correction)


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
