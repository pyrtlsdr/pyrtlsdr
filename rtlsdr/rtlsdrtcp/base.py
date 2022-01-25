from __future__ import division
import sys
import time
import select
import socket
import struct
import errno
import traceback
import json

try:
    from itertools import izip
except ImportError:
    izip = zip

has_numpy = True
try:
    import numpy as np
except ImportError:
    has_numpy = False

PY2 = sys.version_info[0] == 2

DEFAULT_READ_SIZE = 1024
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


class RtlSdrTcpBase(object):
    """Base class for all ``rtlsdrtcp`` functionality

    Arguments:
        device_index (:obj:`int`, optional):
        test_mode_enabled (:obj:`bool`, optional):
        hostname (:obj:`str`, optional):
        port (:obj:`int`, optional):
    """
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

    def packed_bytes_to_iq(self, bytes):
        """A direct copy of :meth:`rtlsdr.BaseRtlSdr.packed_bytes_to_iq`
        """

        if has_numpy:
            # use NumPy array
            data = np.ctypeslib.as_array(bytes)
            iq = data.astype(np.float64).view(np.complex128)
            iq /= 127.5
            iq -= (1 + 1j)
        else:
            # use normal list
            iq = [complex(i/(255/2) - 1, q/(255/2) - 1) for i, q in izip(bytes[::2], bytes[1::2])]

        return iq


API_METHODS = (
    'get_center_freq', 'set_center_freq',
    'get_sample_rate', 'set_sample_rate',
    'get_bandwidth', 'set_bandwidth',
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
    'bandwidth',
    'gain',
    'freq_correction',
}


class MessageBase(object):
    """Base class for messages sent between clients and servers.

    Handles serialization/deserialization and communication with
    socket type objects.

    Attributes:
        timestamp (float): Timestamp given from :func:`time.time`
        header (dict): A ``dict`` containing message type and payload information
        data: The payload containing either the request or response data
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
        """Reads data from the socket and parses an instance of :class:`MessageBase`

        Arguments:
            sock: The :class:`~socket.socket` object to read from

        """
        header = cls._recv(sock)
        if not PY2:
            header = header.decode()
        kwargs = json.loads(header)
        if kwargs.get('ACK'):
            cls = AckMessage
        return cls(**kwargs)

    def get_header(self, **kwargs):
        """Builds the header data for the message

        The :attr:`timestamp` is added to the header if not already present.

        Returns:
            dict:
        """
        d = {}
        ts = kwargs.get('timestamp')
        if ts is None:
            ts = time.time()
        d['timestamp'] = ts
        return d

    def get_data(self, **kwargs):
        return kwargs.get('data', kwargs.get('header', {}).get('data'))

    def send_message(self, sock):
        """Serializes and sends the message

        Arguments:
            sock: The :class:`~socket.socket` object to write to

        """
        header, data = self._serialize()
        self._send(sock, header)

    def get_response(self, sock):
        """Waits for a specific response message

        The message class returned from :meth:`get_response_class` is used
        to parse the message (called from :meth:`from_remote`)

        Arguments:
            sock: The :class:`~socket.socket` object to read from
        """
        cls = self.get_response_class()
        return cls.from_remote(sock)

    def get_ack_response(self, sock):
        return AckMessage.from_remote(sock)

    def _serialize(self):
        """Serializes the message header and data
        """
        struct_fmt = self.header.get('struct_fmt')
        if struct_fmt is not None:
            return json.dumps(self.header), self.data
        data = self.header.copy()
        data.setdefault('data', self.data)
        return json.dumps(data), None



class AckMessage(MessageBase):
    """Simple message type meant for ACKnolegemnt of message receipt
    """
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
            struct_fmt = str(struct_fmt)
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
            struct_fmt = str(struct_fmt)
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
