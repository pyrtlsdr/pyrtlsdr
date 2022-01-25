
import socket

from .base import (
    CommunicationError,
    RtlSdrTcpBase,
    ClientMessage,
    ServerMessage,
    AckMessage,
    DEFAULT_READ_SIZE,
)

class RtlSdrTcpClient(RtlSdrTcpBase):

    """Client object that connects to a remote server.

    Exposes most of the methods and descriptors that are available in the
    RtlSdr class in a transparent manner allowing an interface that is nearly
    identical to the core API.

    """

    def __init__(self, device_index=0, test_mode_enabled=False,
                 hostname='127.0.0.1', port=None):
        super(RtlSdrTcpClient, self).__init__(device_index, test_mode_enabled,
                                              hostname, port)
        self.open()

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
                raise CommunicationError('ACK message received as "NAK"')
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

    def get_bandwidth(self):
        return self._communicate_descriptor_get('bandwidth')

    def set_bandwidth(self, value):
        self._communicate_descriptor_set('bandwidth', value)

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

    def read_bytes(self, num_bytes=DEFAULT_READ_SIZE):
        return self._communicate_method('read_bytes', num_bytes)

    def read_samples(self, num_samples=DEFAULT_READ_SIZE):
        raw_data = self._communicate_method('read_samples', num_samples)
        iq = self.packed_bytes_to_iq(raw_data)
        return iq

    def read_samples_async(self, *args):
        raise NotImplementedError('Async read not available in TCP mode')

    def read_bytes_async(self, *args):
        raise NotImplementedError('Async read not available in TCP mode')

    center_freq = fc = property(get_center_freq, set_center_freq)
    sample_rate = rs = property(get_sample_rate, set_sample_rate)
    bandwidth = property(get_bandwidth, set_bandwidth)
    gain = property(get_gain, set_gain)
    freq_correction = property(get_freq_correction, set_freq_correction)
