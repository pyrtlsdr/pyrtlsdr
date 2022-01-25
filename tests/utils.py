from __future__ import division
import os
import time
import random

try:
    import numpy as np
except ImportError:
    np = None

import pytest

from conftest import is_travisci

def iter_test_samples(num_samples=None):
    count = 0
    complete = False
    while not complete:
        for i, q in zip(range(256), range(255, -1, -1)):
            yield i, q
            if num_samples is not None:
                count += 1
                if count >= num_samples:
                    complete = True
                    break

def iter_test_bytes(num_bytes=None):
    count = 0
    if num_bytes is not None:
        num_samples = num_bytes // 2
    else:
        num_samples = None
    complete = False
    while not complete:
        for i, q in iter_test_samples(num_samples):
            yield i
            if num_bytes is not None:
                count += 1
                if count >= num_bytes:
                    complete = True
                    break
            yield q
            if num_bytes is not None:
                count += 1
                if count >= num_bytes:
                    complete = True
                    break

def check_generated_data(samples, direct_sampling=0, use_numpy=True):
    if not is_travisci():
        return
    test_len = 256 * (len(samples) // 256)
    samples = samples[:test_len]
    if direct_sampling != 0:
        if direct_sampling == 1:
            a = [i for i, q in iter_test_samples(test_len)]
        elif direct_sampling == 2:
            a = [q for i, q in iter_test_samples(test_len)]
        if isinstance(samples, tuple):
            samples = list(samples)
        assert a == samples
        return
    if use_numpy and np is not None:
        a = np.fromiter((complex(i, q) for i, q in iter_test_samples(test_len)), dtype='complex')
        a /= (255/2)
        a -= (1 + 1j)
        assert np.array_equal(samples, a)
    else:
        a = [complex(i/(255/2) - 1, q/(255/2) - 1) for i, q in iter_test_samples(test_len)]
        assert samples == a

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


def generic_test(sdr, test_async=True, test_exceptions=True, use_numpy=True):
    """Functionality checks common to all tests
    Instantiates the given subclass of :class:`rtlsdr.RtlSdr`,
    checks get/set methods for sample_rate, center_freq and gain,
    then reads 1024 samples.

    Returns the instance for further tests.
    """
    print('Testing %r' % (sdr))

    sdr.rs = 2.048e6
    assert check_close(7, 2.048e6, sdr.rs)
    print('sample_rate: %s' % (sdr.rs))

    bw = sdr.rs / 2
    print('setting bandwidth to {}'.format(bw))
    sdr.bandwidth = bw
    assert check_close(7, bw, sdr.bandwidth)
    print('applied bandwidth={}'.format(sdr.bandwidth))

    prev_fc = sdr.fc
    sdr.fc = prev_fc + 1e6
    assert check_close(7, prev_fc + 1e6, sdr.fc)
    print('center_freq: %s' % (sdr.fc))

    sdr.gain = 10
    assert check_close(2, 10, sdr.gain)
    print('gain: %s' % (sdr.gain))

    samples = sdr.read_samples(1024)
    assert len(samples) == 1024
    check_generated_data(samples, use_numpy=use_numpy)
    print('read %s samples' % (len(samples)))

    sdr.set_direct_sampling('i')
    samples = sdr.read_bytes(1024)
    check_generated_data(samples, 1, use_numpy=use_numpy)

    sdr.set_direct_sampling('q')
    samples = sdr.read_bytes(1024)
    check_generated_data(samples, 2, use_numpy=use_numpy)

    if test_exceptions:
        with pytest.raises(SyntaxError):
            sdr.set_direct_sampling('foo')

    sdr.set_direct_sampling(0)

    if test_async:
        async_read_test(sdr, use_numpy=use_numpy)


def async_read_test(sdr, read_size=1024, num_callbacks=2, bytes_mode=False, use_numpy=True):
    from rtlsdr.helpers import limit_calls
    @limit_calls(num_callbacks)
    def read_callback(data, rtlsdr_obj):
        if bytes_mode:
            s = 'read %s bytes'
        else:
            s = 'read %s samples'
        print(s % len(data))
        assert len(data) == read_size
        check_generated_data(data, use_numpy=use_numpy)
    print('testing async read')
    if bytes_mode:
        sdr.read_bytes_async(read_callback, read_size)
    else:
        sdr.read_samples_async(read_callback, read_size)


def async_bytes_test(sdr, read_size=1024, num_callbacks=2):
    _async_read_test(sdr, read_size, num_callbacks, bytes_mode=True)
