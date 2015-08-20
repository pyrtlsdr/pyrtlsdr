import sys
import time
import threading
import socket
import argparse

PY2 = sys.version_info[0] == 2
if PY2:
    from SocketServer import TCPServer, BaseRequestHandler
else:
    from socketserver import TCPServer, BaseRequestHandler

try:
    import numpy as np
except ImportError:
    np = None

try:
    from rtlsdr import RtlSdr
    from helpers import numpyjson
except ImportError:
    from .rtlsdr import RtlSdr
    from .helpers import numpyjson

MAX_BUFFER_SIZE = 4096

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
    def open(self, device_index=0, test_mode_enabled=False):
        if not self.device_ready:
            return
        super(RtlSdrTcpServer, self).open(device_index, test_mode_enabled)
    def run(self):
        if self.server_thread is None:
            self.server_thread = ServerThread(self)
        if self.server_thread.running.is_set():
            return
        self.server_thread.start()
        self.server_thread.running.wait()
    def run_forever(self):
        self.run()
        while True:
            try:
                self.server_thread.stopped.wait(1.)
            except KeyboardInterrupt:
                self.close()
                break
    def close(self):
        if self.server_thread is not None:
            if self.server_thread.running.is_set():
                self.server_thread.stop()
            self.server_thread = None
        super(RtlSdrTcpServer, self).close()

class ServerThread(threading.Thread):
    def __init__(self, rtl_sdr):
        super(ServerThread, self).__init__()
        self.rtl_sdr = rtl_sdr
        self.running = threading.Event()
        self.stopped = threading.Event()
    def run(self):
        self.server = Server(self.rtl_sdr)
        rtl_sdr = self.rtl_sdr
        rtl_sdr.device_ready = True
        rtl_sdr.open(rtl_sdr.device_index, rtl_sdr.test_mode_enabled)
        self.running.set()
        self.server.serve_forever()
        self.running.clear()
        rtl_sdr.device_ready = False
        self.stopped.set()
    def stop(self):
        self.server.shutdown()
        self.stopped.wait()

class Server(TCPServer):
    REQUEST_RECV_SIZE = 1024
    def __init__(self, rtl_sdr):
        self.rtl_sdr = rtl_sdr
        server_addr = (rtl_sdr.hostname, rtl_sdr.port)
        TCPServer.__init__(self, server_addr, RequestHandler)

API_METHODS = {
    'get_center_freq':{'return_type':float},
    'set_center_freq':{'args':float},
    'get_sample_rate':{'return_type':float},
    'set_sample_rate':{'args':float},
    'get_gain':{'return_type':'float'},
    'set_gain':{'args':[float, str]},
    'get_freq_correction':{'return_type':int},
    'set_freq_correction':{'args':int},
    'get_gains':{'return_type':list},
    'get_tuner_type':{'return_type':int},
    'set_direct_sampling':{'args':bool},
    'read_samples':{'args':int, 'return_type':'numpy'},
    'read_samples_async':{'args':int, 'return_type':'numpy'}
}
API_DESCRIPTORS = {
    'center_freq':('get_center_freq', 'set_center_freq'),
    'fc':('get_center_freq', 'set_center_freq'),
    'sample_rate':('get_sample_rate', 'set_sample_rate'),
    'rs':('get_sample_rate', 'set_sample_rate'),
    'gain':('get_gain', 'set_gain'),
    'freq_correction':('get_freq_correction', 'set_freq_correction')
}

class MessageBase(object):
    def __init__(self, **kwargs):
        self.data_len = None
        self.timestamp = kwargs.get('timestamp')
        self.header = self.get_header(**kwargs)
        self.data = self.get_data(**kwargs)
        self.data_is_complex = False
    @classmethod
    def from_remote(cls, sock):
        header = sock.recv(MAX_BUFFER_SIZE)
        kwargs = numpyjson.loads(header)
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
        return kwargs.get('data')
    def send_message(self, sock):
        header, data = self._serialize()
        sock.sendall(header)
    def get_response(self, sock):
        cls = self.get_response_class()
        return cls.from_remote(sock)
    def get_ack_response(self, sock):
        return AckMessage.from_remote(sock)
    def _serialize(self):
        if not self.data_is_complex:
            d = self.header.copy()
            d['data'] = self.data
            return numpyjson.dumps(d), None
        data = self._serialize_data()
        if data is not None:
            self.data_len = len(data)
        header = self._serialize_header()
        return header, data
    def _serialize_header(self):
        header = self.header
        header['data_len'] = self.data_len
        return numpyjson.dumps(self.header)
    def _serialize_data(self):
        return numpyjson.dumps(self.data)

class AckMessage(MessageBase):
    def get_header(self, **kwargs):
        d = super(AckMessage, self).get_header(**kwargs)
        d['ACK'] = True
        d['ok'] = kwargs.get('ok', True)
        return d

class ServerMessage(MessageBase):
    def __init__(self, **kwargs):
        super(ServerMessage, self).__init__(**kwargs)
        is_complex = False
        if self.data is not None:
            if np is not None and isinstance(self.data, np.ndarray):
                is_complex = True
            elif isinstance(self.data, list) and len(self.data):
                if isinstance(self.data[0], complex):
                    is_complex = True
        self.data_is_complex = is_complex
    @classmethod
    def from_remote(cls, sock):
        header = sock.recv(MAX_BUFFER_SIZE)
        kwargs = numpyjson.loads(header)
        data_len = kwargs.get('data_len')
        data = kwargs.get('data')
        if data_len is None or data is not None:
            return cls(**kwargs)
        ack_msg = AckMessage()
        ack_msg.send_message(sock)
        recv = None
        while data_len > 0:
            _recv = sock.recv(MAX_BUFFER_SIZE)
            if recv is None:
                recv = _recv
            else:
                recv += _recv
            data_len -= len(_recv)
        kwargs['data'] = numpyjson.loads(recv)
        return cls(**kwargs)
    def send_message(self, sock):
        header, data = self._serialize()
        sock.sendall(header)
        if data is not None:
            ack = self.get_ack_response(sock)
            if not ack.header.get('ok'):
                return False
            data_len = self.data_len
            while data_len > 0:
                sent = sock.send(data)
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
    def handle(self):
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
    def handle_method_call(self, rx_message):
        rtl_sdr = self.server.rtl_sdr
        method_name = rx_message.header.get('name')
        arg = rx_message.data
        if method_name not in API_METHODS:
            return False
        try:
            m = getattr(rtl_sdr, method_name)
        except AttributeError:
            return False
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
        api_data = API_DESCRIPTORS.get(prop_name)
        if api_data is None:
            return False
        setattr(rtl_sdr, prop_name, value)
        tx_message = ServerMessage(client_message=rx_message)
        tx_message.send_message(self.request)
    def handle_prop_get(self, rx_message):
        prop_name = rx_message.header.get('name')
        api_data = API_DESCRIPTORS.get(prop_name)
        if api_data is None:
            return False
        rtl_sdr = self.server.rtl_sdr
        value = getattr(rtl_sdr, prop_name)
        tx_message = ServerMessage(client_message=rx_message, data=value)
        tx_message.send_message(self.request)

class RtlSdrTcpClient(RtlSdrTcpBase):
    def open(self, *args):
        self.device_opened = True
    def close(self):
        self.device_opened = False
    def _build_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.hostname, self.port))
        return s
    def _communicate(self, tx_message):
        s = self._build_socket()
        resp = tx_message.send_message(s)
        if isinstance(resp, ServerMessage):
            if not resp.header.get('success'):
                ## TODO: raise an exception?
                pass
            return resp.data
        elif isinstance(resp, AckMessage):
            if not resp.header.get('ok'):
                ## TODO: raise an exception?
                pass
        s.close()
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
    def read_samples(self, num_samples=RtlSdr.DEFAULT_READ_SIZE):
        return self._communicate_method('read_samples', num_samples)
    center_freq = fc = property(get_center_freq, set_center_freq)
    sample_rate = rs = property(get_sample_rate, set_sample_rate)
    gain = property(get_gain, set_gain)
    freq_correction = property(get_freq_correction, set_freq_correction)

def run_server():
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

def test():
    import time
    server = RtlSdrTcpServer()
    server.run()
    client = RtlSdrTcpClient()
    test_props = [
        ['sample_rate', 2e6],
        ['center_freq', 6e6],
        ['gain', 10.],
        ['freq_correction', 20]
    ]
    try:
        gains = client.get_gains()
        gains = [gain / 10. for gain in gains]
        print('gains: ', gains)
        for prop_name, set_value in test_props:
            if prop_name != 'gain':
                value = getattr(client, prop_name)
                print('%s initial value: %s' % (prop_name, value))
            else:
                set_value = gains[1]
            setattr(client, prop_name, set_value)
            value = getattr(client, prop_name)
            print('%s set to %s, real value: %s' % (prop_name, set_value, value))
            assert int(value) == int(set_value)
            time.sleep(.2)
        tuner_type = client.get_tuner_type()
        print('tuner_type: ', tuner_type)
        for num_samples in [1024, 4096, 16384, 65536, 131072]:
            print('Reading %s samples...' % (num_samples))
            samples = client.read_samples(num_samples)
            print('%s samples received' % (len(samples)))
            assert len(samples) == num_samples
    finally:
        server.close()
    print('Complete')

if __name__ == '__main__':
    run_server()
