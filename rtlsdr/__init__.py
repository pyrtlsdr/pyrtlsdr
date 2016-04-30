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


try:                from  librtlsdr import librtlsdr
except ImportError: from .librtlsdr import librtlsdr
try:                from  rtlsdr import RtlSdr
except ImportError: from .rtlsdr import RtlSdr
try:                from rtlsdrtcp import RtlSdrTcpServer, RtlSdrTcpClient
except ImportError: from .rtlsdrtcp import RtlSdrTcpServer, RtlSdrTcpClient
try:                from  helpers import limit_calls, limit_time
except ImportError: from .helpers import limit_calls, limit_time

try:
    from rtlsdraio import RtlSdrAio, AIO_AVAILABLE
except ImportError:
    from .rtlsdraio import RtlSdrAio, AIO_AVAILABLE

if AIO_AVAILABLE:
    RtlSdr = RtlSdrAio


__all__  = ['librtlsdr', 'RtlSdr', 'RtlSdrTcpServer', 'RtlSdrTcpClient',
            'limit_calls', 'limit_time']
