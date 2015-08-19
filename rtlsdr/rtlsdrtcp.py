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
        else:
            ack = AckMessage()
            ack.send_message(sock)
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
    '''Expected data:
        Method call with arg:
            method_name!arg
        Method call without arg:
            method_name!
        Descriptor set:
            descriptor_name=value
        Descriptor get:
            descriptor_name?
    '''
    def handle(self):
        recv_size = self.server.REQUEST_RECV_SIZE
        data = self.data = self.request.recv(recv_size)
        print('RX: ', data)
        if '!' in data:
            resp, resp_type = self.handle_method_call(data)
        elif '=' in data:
            resp, resp_type = self.handle_prop_set(data)
        elif '?' in data:
            resp, resp_type = self.handle_prop_get(data)
        else:
            resp, resp_type = None, None
        if resp is not None or resp_type is not None:
            resp_data = self.format_response(resp, resp_type)
            if isinstance(resp_data, list):
                self.request.sendall(resp_data[0])
                client_resp = self.request.recv(1024)
                self.request.sendall(resp_data[1])
            else:
                self.request.sendall(resp_data)
    def handle_method_call(self, data):
        method_name, arg = data.split('!')
        method_name = method_name.strip()
        arg = arg.strip()
        if method_name not in API_METHODS:
            return None, None
        return self._handle_method_call(method_name, arg)
    def _handle_method_call(self, method_name, arg):
        rtl_sdr = self.server.rtl_sdr
        api_data = API_METHODS.get(method_name)
        try:
            m = getattr(rtl_sdr, method_name.strip())
        except AttributeError:
            return None, None
        if 'args' in api_data and not arg:
            return None, None
        _arg = None
        if isinstance(api_data.get('args'), list):
            for arg_type in api_data['args']:
                try:
                    _arg = arg_type(arg)
                except ValueError:
                    _arg = None
                if _arg is not None:
                    break
            if _arg is None:
                return None, None
        elif 'args' in api_data:
            try:
                _arg = api_data['args'](arg)
            except ValueError:
                return None, None
        if _arg is not None:
            resp = m(_arg)
        else:
            resp = m()
        resp_type = api_data.get('return_type')
        if resp_type is None:
            resp_type = '__ack__'
        return resp, resp_type
    def handle_prop_set(self, data):
        prop_name, value = data.split('=')
        prop_name = prop_name.strip()
        value = value.strip()
        api_data = API_DESCRIPTORS.get(prop_name)
        if api_data is None:
            return None, None
        method_name = api_data[1]
        return self._handle_method_call(method_name, value)
    def handle_prop_get(self, data):
        prop_name = data.split('?')[0].strip()
        api_data = API_DESCRIPTORS.get(prop_name)
        if api_data is None:
            return None, None
        rtl_sdr = self.server.rtl_sdr
        value = getattr(rtl_sdr, prop_name)
        resp_type = API_METHODS.get(api_data[0], {}).get('return_type')
        return value, resp_type
    def format_response(self, resp, resp_type):
        d = {'success':True}
        if resp_type != '__ack__':
            d.update({'type':str(resp_type), 'value':resp})
        msg = numpyjson.dumps(d)
        if len(msg) <= MAX_BUFFER_SIZE:
            return msg
        header = {'success':True, 'multipart':True, 'payload_size':len(msg)}
        header = numpyjson.dumps(header)
        return [header, msg]


class RtlSdrTcpClient(RtlSdrTcpBase):
    def open(self, *args):
        self.device_opened = True
    def close(self):
        self.device_opened = False
    def _build_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.hostname, self.port))
        return s
    def _communicate(self, tx_message, recv_size=MAX_BUFFER_SIZE):
        s = self._build_socket()
        s.sendall(tx_message)
        resp = s.recv(recv_size)
        if resp:
            resp = numpyjson.loads(resp)
            if isinstance(resp, dict):
                if resp.get('multipart'):
                    msg_len = resp.get('payload_size')
                    s.sendall('ready')
                    resp = ''
                    while len(resp) < msg_len:
                        resp += s.recv(recv_size)
                    resp = numpyjson.loads(resp)
                resp = resp.get('value')
        s.close()
        return resp
    def _communicate_method(self, method_name, arg='', recv_size=MAX_BUFFER_SIZE):
        msg = '!'.join([method_name, numpyjson.dumps(arg)])
        return self._communicate(msg, recv_size)
    def _communicate_descriptor(self, prop_name, value=None, recv_size=MAX_BUFFER_SIZE):
        if value is None:
            msg = '%s?' % (prop_name)
        else:
            msg = '='.join([prop_name, numpyjson.dumps(value)])
        return self._communicate(msg, recv_size)
    def get_center_freq(self):
        return self._communicate_descriptor('fc')
    def set_center_freq(self, value):
        self._communicate_descriptor('fc', value)
    def get_sample_rate(self):
        return self._communicate_descriptor('rs')
    def set_sample_rate(self, value):
        self._communicate_descriptor('rs', value)
    def get_gain(self):
        return self._communicate_descriptor('gain')
    def set_gain(self, value):
        self._communicate_descriptor('gain', value)
    def get_freq_correction(self):
        return self._communicate_descriptor('freq_correction')
    def set_freq_correction(self, value):
        self._communicate_descriptor('freq_correction', value)
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
