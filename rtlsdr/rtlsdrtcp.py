import sys
import threading
import socket

PY2 = sys.version_info[0] == 2
if PY2:
    from SocketServer import TCPServer, BaseRequestHandler
else:
    from socketserver import TCPServer, BaseRequestHandler

try:
    from rtlsdr import RtlSdr
    from helpers import numpyjson
except ImportError:
    from .rtlsdr import RtlSdr
    from .helpers import numpyjson


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
            if self.server_thread is None:
                self.build_server()
            return
        super(RtlSdrTcpServer, self).open(device_index, test_mode_enabled)
    def build_server(self):
        self.server_thread = ServerThread(self)
    def run_forever(self):
        self.server_thread.start()
        while True:
            try:
                self.server_thread.stopped.wait(1.)
            except KeyboardInterrupt:
                self.close()
                break
    def close(self):
        self.server_thread.stop()
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
        if resp is not None:
            resp_data = self.format_response(resp, resp_type)
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
        if isinstance(api_data['args'], list):
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
        return resp, api_data.get('return_type')
    def handle_prop_set(self, data):
        prop_name, value = data.split('=')
        prop_name = prop_name.strip()
        value = value.strip()
        api_data = API_DESCRIPTORS.get(prop_name)
        if api_data is None:
            return None, None
        method_name = API_METHODS.get(api_data[1])
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
        return numpyjson.dumps({'type':str(resp_type), 'value':resp})

class RtlSdrTcpClient(RtlSdrTcpBase):
    def open(self, *args):
        self.device_opened = True
    def _build_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.hostname, self.port))
        return s
    def _communicate(self, tx_message, recv_size=1024):
        s = self._build_socket()
        s.sendall(tx_message)
        resp = s.recv(recv_size)
        if resp:
            resp = numpyjson.loads(resp)
            if isinstance(resp, dict):
                resp = resp['value']
        s.close()
        return resp
    def _communicate_method(self, method_name, arg='', recv_size=1024):
        msg = '!'.join([method_name, numpyjson.dumps(arg)])
        return self._communicate(msg, recv_size)
    def _communicate_descriptor(self, prop_name, value=None, recv_size=1024):
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
        recv_size = num_samples * 32
        return self._communicate_method('read_samples', num_samples, recv_size)
    center_freq = fc = property(get_center_freq, set_center_freq)
    sample_rate = rs = property(get_sample_rate, set_sample_rate)
    gain = property(get_gain, set_gain)
    freq_correction = property(get_freq_correction, set_freq_correction)
