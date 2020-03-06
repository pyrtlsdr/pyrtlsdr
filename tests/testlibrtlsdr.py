import time
from ctypes import *

try:
    from utils import iter_test_bytes, iter_test_samples
except ImportError:
    # add no-op versions of above functions so this module can be used
    # to monkeypatch librtlsdr in rtfd.org builds (see setup.py)
    def iter_test_bytes():
        while True:
            yield 0
    def iter_test_samples():
        while True:
            yield 0, 0

ERROR_CODE = 0

class p_rtlsdr_dev(object):
    def __init__(self, *args):
        pass

class LibRtlSdr(object):
    async_callback = None
    async_generator = None
    NUM_FAKE_DEVICES = 32
    def __init__(self):
        self.fc = 1e6
        self.rs = 2e6
        self.bw = 2e6
        self.err_ppm = 0
        self.gain = 0
        self.gains = list(range(0, 300, 25))
        self.gain_mode = 0
        self.agc_mode = 0
        self.direct_sampling = 0
    def rtlsdr_get_device_count(self):
        if ERROR_CODE != 0:
            return ERROR_CODE
        return self.NUM_FAKE_DEVICES
    def rtlsdr_get_device_usb_strings(self, device_index, manufact, product, serial):
        if ERROR_CODE != 0:
            return ERROR_CODE
        if device_index >= self.NUM_FAKE_DEVICES:
            return -1
        ser_string = '%08d' % (device_index)
        for i, c in enumerate(ser_string):
            serial[i] = ord(c)
        return 0
    def rtlsdr_get_index_by_serial(self, serial):
        if ERROR_CODE != 0:
            return ERROR_CODE
        if not serial.isdigit():
            return -1
        i = int(serial)
        if i >= self.NUM_FAKE_DEVICES:
            return -3
        return i
    def rtlsdr_open(self, *args):
        self.fc = 1e6
        self.rs = 2e6
        self.bw = 2e6
        self.err_ppm = 0
        self.gain = 0
        self.gains = list(range(0, 300, 25))
        self.gain_mode = 0
        self.agc_mode = 0
        self.direct_sampling = 0
        return ERROR_CODE
    def rtlsdr_set_testmode(self, *args):
        return ERROR_CODE
    def rtlsdr_reset_buffer(self, *args):
        return ERROR_CODE
    def rtlsdr_close(self, *args):
        return ERROR_CODE
    def rtlsdr_set_center_freq(self, dev_p, fc):
        self.fc = fc
        return ERROR_CODE
    def rtlsdr_get_center_freq(self, *args):
        if ERROR_CODE != 0:
            return ERROR_CODE
        return self.fc
    def rtlsdr_set_freq_correction(self, dev_p, err_ppm):
        self.err_ppm = err_ppm
        return ERROR_CODE
    def rtlsdr_get_freq_correction(self, dev_p):
        if ERROR_CODE != 0:
            return ERROR_CODE
        return self.err_ppm
    def rtlsdr_set_sample_rate(self, dev_p, rs):
        self.rs = rs
        return ERROR_CODE
    def rtlsdr_set_and_get_tuner_bandwidth(self, dev_p, bw, applied_bw, apply_bw):
        if apply_bw == 0:
            applied_bw._obj.value = self.bw
        else:
            self.bw = bw
        return ERROR_CODE
    def rtlsdr_set_tuner_bandwidth(self, dev_p, bw):
        return ERROR_CODE
    def rtlsdr_get_sample_rate(self, *args):
        if ERROR_CODE != 0:
            return ERROR_CODE
        return self.rs
    def rtlsdr_set_tuner_gain(self, dev_p, gain):
        self.gain = gain
        return ERROR_CODE
    def rtlsdr_get_tuner_gain(self, *args):
        if ERROR_CODE != 0:
            return ERROR_CODE
        return self.gain
    def rtlsdr_get_tuner_gains(self, dev_p, buf):
        for i, gain in enumerate(self.gains):
            buf[i] = gain
        return len(self.gains)
    def rtlsdr_set_tuner_gain_mode(self, dev_p, mode):
        self.gain_mode = mode
        return ERROR_CODE
    def rtlsdr_set_agc_mode(self, dev_p, mode):
        self.agc_mode = mode
        return ERROR_CODE
    def rtlsdr_set_direct_sampling(self, dev_p, direct):
        self.direct_sampling = direct
        return ERROR_CODE
    def rtlsdr_get_tuner_type(self, *args):
        return ERROR_CODE
    def rtlsdr_read_sync(self, dev_p, buf, num_bytes, num_bytes_read):
        if ERROR_CODE != 0:
            return ERROR_CODE
        num_bytes_read._obj.value = num_bytes
        self._generate_fake_data(num_bytes, buf)
        return 0
    def _generate_fake_data(self, data_len, buf=None):
        if buf is None:
            array_type = (c_ubyte*data_len)
            buf = array_type()
        direct_sampling = self.direct_sampling
        if direct_sampling == 0:
            iq = iter_test_bytes()
            for i in range(data_len):
                buf[i] = next(iq)
        else:
            iq = iter_test_samples()
            buf_index = 0
            for x in range(data_len):
                i, q = next(iq)
                if direct_sampling == 1:
                    buf[x] = i
                elif direct_sampling == 2:
                    buf[x] = q
                buf_index += 1
        return buf
    def rtlsdr_read_async(self, dev_p, callback, context, buf_num, num_bytes):
        if ERROR_CODE != 0:
            return ERROR_CODE
        self.async_callback = callback
        self.async_context = context
        self.async_generator = AsyncGenerator(self, num_bytes)
        self.async_generator.run()
        self.async_generator = None
        return ERROR_CODE
    def rtlsdr_cancel_async(self, *args):
        if self.async_generator is not None:
            self.async_generator.running = False
        return ERROR_CODE

class AsyncGenerator(object):
    """Simple object to emulate `rtlsdr_read_async` behavior.
    Used by :meth:`DummyRtlSdr.read_bytes_async`
    and :meth:`DummyRtlSdr.read_samples_async`
    """
    def __init__(self, libobj, num_bytes):
        self.libobj = libobj
        self.num_bytes = num_bytes
        num_samples = num_bytes / 2

        # Guess how long it SHOULD take to read based off of the sample rate
        self.timeout = 1. / libobj.rs * num_samples
        self.running = False

    def run(self):
        libobj = self.libobj
        self.running = True
        while self.running:
            buf = libobj._generate_fake_data(self.num_bytes)
            libobj.async_callback(buf, self.num_bytes, libobj.async_context)
            time.sleep(self.timeout)

librtlsdr = LibRtlSdr()

tuner_bandwidth_supported = True
tuner_set_bandwidth_supported = True

def rtlsdr_read_async_cb_t(cb):
    return cb
