import time
import random
from ctypes import *

class p_rtlsdr_dev(object):
    def __init__(self, *args):
        pass

class LibRtlSdr(object):
    async_callback = None
    async_generator = None
    def __init__(self):
        self.fc = 1e6
        self.rs = 2e6
        self.err_ppm = 0
        self.gain = 0
        self.gains = list(range(0, 300, 25))
        self.gain_mode = 0
        self.agc_mode = 0
        self.direct_sampling = 0
    def rtlsdr_open(self, *args):
        return 0
    def rtlsdr_set_testmode(self, *args):
        return 0
    def rtlsdr_reset_buffer(self, *args):
        return 0
    def rtlsdr_close(self, *args):
        return 0
    def rtlsdr_set_center_freq(self, dev_p, fc):
        self.fc = fc
        return 0
    def rtlsdr_get_center_freq(self, *args):
        return self.fc
    def rtlsdr_set_freq_correction(self, dev_p, err_ppm):
        self.err_ppm = err_ppm
        return 0
    def rtlsdr_set_sample_rate(self, dev_p, rs):
        self.rs = rs
        return 0
    def rtlsdr_get_sample_rate(self, *args):
        return self.rs
    def rtlsdr_set_tuner_gain(self, dev_p, gain):
        self.gain = gain
        return 0
    def rtlsdr_get_tuner_gain(self, *args):
        return self.gain
    def rtlsdr_get_tuner_gains(self, dev_p, buf):
        for i, gain in enumerate(self.gains):
            buf[i] = gain
        return len(self.gains)
    def rtlsdr_set_tuner_gain_mode(self, dev_p, mode):
        self.gain_mode = mode
        return 0
    def rtlsdr_set_agc_mode(self, dev_p, mode):
        self.agc_mode = mode
        return 0
    def rtlsdr_set_direct_sampling(self, dev_p, direct):
        self.direct_sampling = direct
        return 0
    def rtlsdr_get_tuner_type(self, *args):
        return 0
    def rtlsdr_read_sync(self, dev_p, buf, num_bytes, num_bytes_read):
        num_bytes_read._obj.value = num_bytes
        self._generate_fake_data(num_bytes, buf)
        return 0
    def _generate_fake_data(self, data_len, buf=None):
        if buf is None:
            array_type = (c_ubyte*data_len)
            buf = array_type()
        for i in range(data_len):
            buf[i] = random.randint(0, 255)
        return buf
    def rtlsdr_read_async(self, dev_p, callback, context, buf_num, num_bytes):
        self.async_callback = callback
        self.async_context = context
        self.async_generator = AsyncGenerator(self, num_bytes)
        self.async_generator.run()
        self.async_generator = None
        return 0
    def rtlsdr_cancel_async(self, *args):
        if self.async_generator is not None:
            self.async_generator.running = False
        return 0

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

def rtlsdr_read_async_cb_t(cb):
    return cb
