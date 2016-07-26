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

import os

RTLSDR_CLIENT_MODE = False
if os.environ.get('RTLSDR_CLIENT_MODE', '').lower() in ['true', '1', 'yes']:
    RTLSDR_CLIENT_MODE = True

if RTLSDR_CLIENT_MODE:
    from .rtlsdrtcp.client import RtlSdrTcpClient
    librtlsdr = None
    RtlSdr = None
    RtlSdrTcpServer = None
    RtlSdrAio = None
    AIO_AVAILABLE = False
else:
    from .librtlsdr import librtlsdr
    from .rtlsdr import RtlSdr
    from .rtlsdrtcp import RtlSdrTcpServer, RtlSdrTcpClient
    from .helpers import limit_calls, limit_time
    from .rtlsdraio import RtlSdrAio, AIO_AVAILABLE

if AIO_AVAILABLE:
    RtlSdr = RtlSdrAio


__all__  = ['librtlsdr', 'RtlSdr', 'RtlSdrTcpServer', 'RtlSdrTcpClient',
            'limit_calls', 'limit_time']
