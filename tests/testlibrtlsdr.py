import time
from ctypes import *

from utils import iter_test_bytes, iter_test_samples

class p_rtlsdr_dev(object):
    def __init__(self, *args):
        pass

class LibRtlSdr(object):
    async_callback = None
    async_generator = None
    fail_tests = False
    fail_tests_on_open = False
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
    def rtlsdr_open(self, *args):
        if self.fail_tests_on_open:
            return -1
        return 0
    def rtlsdr_set_testmode(self, *args):
        if self.fail_tests:
            return -1
        return 0
    def rtlsdr_reset_buffer(self, *args):
        return 0
    def rtlsdr_close(self, *args):
        return 0
    def rtlsdr_set_center_freq(self, dev_p, fc):
        if self.fail_tests:
            return 0
        self.fc = fc
        return fc
    def rtlsdr_get_center_freq(self, *args):
        if self.fail_tests:
            return 0
        return self.fc
    def rtlsdr_set_freq_correction(self, dev_p, err_ppm):
        if self.fail_tests:
            return -1
        self.err_ppm = err_ppm
        return 0
    def rtlsdr_get_freq_correction(self, dev_p):
        return self.err_ppm
    def rtlsdr_set_sample_rate(self, dev_p, rs):
        if self.fail_tests:
            # should be -EINVAL, but this should still work
            return -1
        self.rs = rs
        return 0
    def rtlsdr_set_and_get_tuner_bandwidth(self, dev_p, bw, applied_bw, apply_bw):
        if self.fail_tests:
            return -1
        if apply_bw == 0:
            applied_bw._obj.value = self.bw
        else:
            self.bw = bw
        return 0
    def rtlsdr_set_tuner_bandwidth(self, dev_p, bw):
        if self.fail_tests:
            return -1
        return 0
    def rtlsdr_get_sample_rate(self, *args):
        if self.fail_tests:
            return 0
        return self.rs
    def rtlsdr_set_tuner_gain(self, dev_p, gain):
        if self.fail_tests:
            return -1
        self.gain = gain
        return 0
    def rtlsdr_get_tuner_gain(self, *args):
        if self.fail_tests:
            return 0
        return self.gain
    def rtlsdr_get_tuner_gains(self, dev_p, buf):
        if self.fail_tests:
            return 0
        for i, gain in enumerate(self.gains):
            buf[i] = gain
        return len(self.gains)
    def rtlsdr_set_tuner_gain_mode(self, dev_p, mode):
        if self.fail_tests:
            return -1
        self.gain_mode = mode
        return 0
    def rtlsdr_set_agc_mode(self, dev_p, mode):
        if self.fail_tests:
            return -1
        self.agc_mode = mode
        return 0
    def rtlsdr_set_direct_sampling(self, dev_p, direct):
        if self.fail_tests:
            return -1
        self.direct_sampling = direct
        return direct
    def rtlsdr_get_tuner_type(self, *args):
        if self.fail_tests:
            return 0
        return 1
    def rtlsdr_read_sync(self, dev_p, buf, num_bytes, num_bytes_read):
        # The api does not indicate a return value for error/success
        if self.fail_tests:
            num_bytes -= 1
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
        if self.fail_tests:
            return -1
        self.async_callback = callback
        self.async_context = context
        self.async_generator = AsyncGenerator(self, num_bytes)
        self.async_generator.run()
        self.async_generator = None
        return 0
    def rtlsdr_cancel_async(self, *args):
        if self.async_generator is not None:
            self.async_generator.running = False
        if self.fail_tests:
            return -1
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
