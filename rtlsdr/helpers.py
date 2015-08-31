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
