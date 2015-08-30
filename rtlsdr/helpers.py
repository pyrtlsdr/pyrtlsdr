#    This file is part of pyrlsdr.
#    Copyright (C) 2013 by Roger <https://github.com/roger-/pyrtlsdr>
#
#    pyrlsdr is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    pyrlsdr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pyrlsdr.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division, print_function
from functools import wraps
import time
import base64
import json
try:
    import numpy as np
except ImportError:
    np = None

def limit_time(max_seconds):
    '''Decorator to cancel async reads after "max_seconds" seconds elapse.
    Call to read_samples_async() or read_bytes_async() must not override context
    parameter.
    '''
    def decorator(f):
        f._start_time = None

        @wraps(f)
        def wrapper(buffer, rtlsdr_obj):
            if f._start_time is None:
                f._start_time = time.time()

            elapsed = time.time() - f._start_time
            if elapsed < max_seconds:
                return f(buffer, rtlsdr_obj)

            rtlsdr_obj.cancel_read_async()

            return

        return wrapper
    return decorator


def limit_calls(max_calls):
    '''Decorator to cancel async reads after "max_calls" function calls occur.
    Call to read_samples_async() or read_bytes_async() must not override context
    parameter.
    '''
    def decorator(f):
        f._num_calls = 0

        @wraps(f)
        def wrapper(buffer, rtlsdr_obj):
            f._num_calls += 1

            if f._num_calls <= max_calls:
                return f(buffer, rtlsdr_obj)

            rtlsdr_obj.cancel_read_async()

            return

        return wrapper
    return decorator


@limit_time(0.01)
@limit_calls(20)
def test_callback(buffer, rtlsdr_obj):
    print('In callback')
    print('   signal mean:', sum(buffer)/len(buffer))

## From http://stackoverflow.com/questions/27909658/


class NumpyEncoder(json.JSONEncoder):
    """JSONEncoder subclass to support serialization of numpy arrays.
    Also handles complex numbers.
    """
    def default(self, obj):
        if np is None:
            if isinstance(obj, complex):
                return dict(__complex__=[obj.real, obj.imag])
        elif isinstance(obj, np.ndarray):
            data_b64 = base64.b64encode(obj.dumps())
            return dict(__ndarray__=data_b64)
        return json.JSONEncoder.default(self, obj)


def json_numpy_obj_hook(dct):
    """Hook to deserialize numpy arrays and complex numbers formatted
    by NumpyEncoder.
    """
    if isinstance(dct, dict):
        if '__ndarray__' in dct:
            data = base64.b64decode(dct['__ndarray__'])
            return np.loads(data)
        elif '__complex__' in dct:
            data = dct['__complex__']
            return complex(*data)
    return dct


class NumpyJson(object):
    """Convenience class to emulate the builtin json module adding
    a JSONEncoder and object hook to support numpy arrays and complex numbers.
    """
    def dumps(self, *args, **kwargs):
        kwargs.setdefault('cls', NumpyEncoder)
        return json.dumps(*args, **kwargs)

    def loads(self, *args, **kwargs):
        kwargs.setdefault('object_hook', json_numpy_obj_hook)
        return json.loads(*args, **kwargs)

    def dump(self, *args, **kwargs):
        kwargs.setdefault('cls', NumpyEncoder)
        return json.dump(*args, **kwargs)

    def load(self, *args, **kwargs):
        kwargs.setdefault('object_hook', json_numpy_obj_hook)
        return json.load(*args, **kwargs)

numpyjson = NumpyJson()
##


def main():
    from rtlsdr import RtlSdr

    sdr = RtlSdr()

    print('Configuring SDR...')
    sdr.rs = 1e6
    sdr.fc = 70e6
    sdr.gain = 5
    print('   sample rate: %0.6f MHz' % (sdr.rs/1e6))
    print('   center ferquency %0.6f MHz' % (sdr.fc/1e6))
    print('   gain: %d dB' % sdr.gain)

    print('Testing callback...')
    sdr.read_samples_async(test_callback)


if __name__ == '__main__':
    main()
