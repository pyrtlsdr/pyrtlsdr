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
    """Decorator to cancel async reads after a specified time period.

    Arguments:
        max_seconds: Number of seconds to wait before cancelling

    Examples:
        Stop reading after 10 seconds:
            >>> @limit_time(10)
            >>> def read_callback(data, context):
            >>>     print('signal mean:', sum(data)/len(data))
            >>> sdr = RtlSdr()
            >>> sdr.read_samples_async(read_callback)

    Notes:
        The context in either :meth:`~rtlsdr.RtlSdr.read_bytes_async`
        or :meth:`~rtlsdr.RtlSdr.read_samples_async` is relied upon and must
        use the default value (the :class:`~rtlsdr.RtlSdr` instance)
    """
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
    """Decorator to cancel async reads after the given number of calls.

    Arguments:
        max_calls (int): Number of calls to wait for before cancelling

    Examples:
        Stop reading after 10 calls:
            >>> @limit_calls(10)
            >>> def read_callback(data, context):
            >>>     print('signal mean:', sum(data)/len(data))
            >>> sdr = RtlSdr()
            >>> sdr.read_samples_async(read_callback)

    Notes:
        See notes in :func:`limit_time`
    """
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
