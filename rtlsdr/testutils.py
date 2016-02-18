import os
import time
import random

try:
    from rtlsdr import RtlSdr
    from helpers import limit_calls
except ImportError:
    from .rtlsdr import RtlSdr
    from .helpers import limit_calls


def is_travisci():
    return all([os.environ.get(key) == 'true' for key in ['CI', 'TRAVIS']])


class DummyRtlSdr(RtlSdr):
    """Subclass of :class:`rtlsdr.RtlSdr` to emulate a real device.
    It does not attempt to communicate with an RTL-SDR device.  This is built
    for testing purposes in environments without a physical device and wouldn't
    be very useful in other situations.
    """
    def __init__(self, device_index=0, test_mode_enabled=False):
        self._center_freq = self.DEFAULT_FC
        self._freq_correction = 0
        self._sample_rate = self.DEFAULT_RS
        self._gain = 0.
        self._gains = list(range(0, 300, 25))
        super(DummyRtlSdr, self).__init__(device_index, test_mode_enabled)

    def open(self, device_index=0, test_mode_enabled=False):
        self.device_opened = True
        self.init_device_values()

    def close(self):
        if not self.device_opened:
            return
        self.device_opened = False

    def set_center_freq(self, freq):
        self._center_freq = freq

    def get_center_freq(self):
        return self._center_freq

    def set_freq_correction(self, err_ppm):
        self._freq_correction = err_ppm

    def get_freq_correction(self):
        return self._freq_correction

    def set_sample_rate(self, rate):
        self._sample_rate = rate

    def get_sample_rate(self):
        return self._sample_rate

    def set_gain(self, gain):
        self._gain = gain

    def get_gain(self):
        return self._gain

    def get_gains(self):
        return self._gains

    def set_manual_gain_enabled(self, enabled):
        pass

    def set_agc_mode(self, enabled):
        pass

    def set_direct_sampling(self, direct):
        pass

    def get_tuner_type(self):
        return 'dummy'

    def read_bytes(self, num_bytes=RtlSdr.DEFAULT_READ_SIZE):
        num_bytes = int(num_bytes)
        return [random.randint(0, 255) for i in range(num_bytes)]
    center_freq = fc = property(get_center_freq, set_center_freq)
    sample_rate = rs = property(get_sample_rate, set_sample_rate)
    gain = property(get_gain, set_gain)
    freq_correction = property(get_freq_correction, set_freq_correction)

    def read_bytes_async(self,
                         callback,
                         num_bytes=RtlSdr.DEFAULT_READ_SIZE,
                         context=None):
        num_bytes = int(num_bytes)
        self._callback_bytes = callback
        if not context:
            context = self
        self.read_async_canceling = False
        self.async_dummy = DummyAsyncSdr(self, num_bytes)
        self.async_dummy.run()
        self.read_async_canceling = False
        self.async_dummy = None

    def _bytes_converter_callback(self, bytes_read):
        if self.read_async_canceling:
            return
        self._callback_bytes(bytes_read, self)

    def read_samples_async(self,
                           callback,
                           num_samples=RtlSdr.DEFAULT_READ_SIZE,
                           context=None):
        num_bytes = 2*num_samples
        self._callback_samples = callback
        self.read_bytes_async(self._samples_converter_callback,
                              num_bytes,
                              context)

    def cancel_read_async(self):
        self.read_async_canceling = True
        self.async_dummy.running = False


class DummyAsyncSdr(object):
    """Simple object to emulate `rtlsdr_read_async` behavior.
    Used by :meth:`DummyRtlSdr.read_bytes_async`
    and :meth:`DummyRtlSdr.read_samples_async`
    """
    def __init__(self, rtlsdr_obj, num_bytes):
        self.rtlsdr_obj = rtlsdr_obj
        self.num_bytes = num_bytes
        num_samples = num_bytes / 2

        # Guess how long it SHOULD take to read based off of the sample rate
        self.timeout = 1. / rtlsdr_obj.rs * num_samples
        self.running = False

    def run(self):
        sdr = self.rtlsdr_obj
        self.running = True
        while self.running:
            bytes_read = sdr.read_bytes(self.num_bytes)
            sdr._bytes_converter_callback(bytes_read)
            time.sleep(self.timeout)


def check_close(num_digits, *args):
    """Checks whether given numbers are equal when rounded to `num_digits`
    """
    div = 10. ** (num_digits - 1)
    last_n = None
    for n in args:
        n /= div
        if last_n is None:
            last_n = n
            continue
        if round(n) != round(last_n):
            return False
        last_n = n
    return True


def build_test_sdr(sdr_cls, *args, **kwargs):
    """Functionality checks common to all tests
    Instanciates the given subclass of :class:`rtlsdr.RtlSdr`,
    checks get/set methods for sample_rate, center_freq and gain,
    then reads 1024 samples.

    Returns the instance for further tests.
    """
    print('Testing %r' % (sdr_cls))
    if is_travisci() and not issubclass(sdr_cls, DummyRtlSdr):
        sdr_cls = DummyRtlSdr
        print('Travis CI detected.  Using dummy class.')

    sdr = sdr_cls(*args, **kwargs)

    prev_rs = sdr.rs
    sdr.rs = prev_rs + 1e6
    assert check_close(7, prev_rs + 1e6, sdr.rs)
    print('sample_rate: %s' % (sdr.rs))

    prev_fc = sdr.fc
    sdr.fc = prev_fc + 1e6
    assert check_close(7, prev_fc + 1e6, sdr.fc)
    print('center_freq: %s' % (sdr.fc))

    sdr.gain = 10
    assert check_close(2, 10, sdr.gain)
    print('gain: %s' % (sdr.gain))

    samples = sdr.read_samples(1024)
    assert len(samples) == 1024
    print('read %s samples' % (len(samples)))

    return sdr


def async_read_test(sdr, read_size=1024, num_callbacks=2, bytes_mode=False):
    @limit_calls(num_callbacks)
    def read_callback(data, rtlsdr_obj):
        if bytes_mode:
            s = 'read %s bytes'
        else:
            s = 'read %s samples'
        print(s % len(data))
        assert len(data) == read_size
    print('testing async read')
    if bytes_mode:
        sdr.read_bytes_async(read_callback, read_size)
    else:
        sdr.read_samples_async(read_callback, read_size)


def async_bytes_test(sdr, read_size=1024, num_callbacks=2):
    _async_read_test(sdr, read_size, num_callbacks, bytes_mode=True)


def test_dummy_rtlsdr():
    sdr = build_test_sdr(DummyRtlSdr)
    async_read_test(sdr)


if __name__ == '__main__':
    test_dummy_rtlsdr()
