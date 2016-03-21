import os
import time
import random


def iter_test_samples(num_samples=None):
    count = 0
    while True:
        for i, q in zip(range(256), range(255, -1, -1)):
            yield i, q
            if num_samples is not None:
                count += 1
                if count >= num_samples:
                    raise StopIteration()

def iter_test_bytes(num_bytes=None):
    count = 0
    if num_bytes is not None:
        num_samples = num_bytes // 2
    else:
        num_samples = None
    while True:
        for i, q in iter_test_samples(num_samples):
            yield i
            if num_bytes is not None:
                count += 1
                if count >= num_bytes:
                    raise StopIteration()
            yield q
            if num_bytes is not None:
                count += 1
                if count >= num_bytes:
                    raise StopIteration()


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


def generic_test(sdr, test_async=True):
    """Functionality checks common to all tests
    Instanciates the given subclass of :class:`rtlsdr.RtlSdr`,
    checks get/set methods for sample_rate, center_freq and gain,
    then reads 1024 samples.

    Returns the instance for further tests.
    """
    print('Testing %r' % (sdr))

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

    if test_async:
        async_read_test(sdr)


def async_read_test(sdr, read_size=1024, num_callbacks=2, bytes_mode=False):
    from rtlsdr.helpers import limit_calls
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
