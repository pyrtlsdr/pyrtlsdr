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
import warnings
import pkg_resources

try:
    __version__ = pkg_resources.require('pyrtlsdr')[0].version
except: # pragma: no cover
    __version__ = 'unknown'

RTLSDR_CLIENT_MODE = False
if os.environ.get('RTLSDR_CLIENT_MODE', '').lower() in ['true', '1', 'yes']:
    RTLSDR_CLIENT_MODE = True

class ClientModeWarning(UserWarning):
    def __init__(self):
        msg = '\n'.join([
            'Running in "client-only" mode: {varname}="{val}"',
            'Only Tcp communication will be available (RtlSdrTcpClient)',
            'If this is was not intended, set "{varname}" to "false" or remove it',
        ]).format(varname='$RTLSDR_CLIENT_MODE', val=os.environ['RTLSDR_CLIENT_MODE'])
        super(ClientModeWarning, self).__init__(msg)

def warn_client_mode():
    def formatwarning(message, category, filename, lineno, line=None):
        return '{}: {}: \n{}\n'.format(filename, category.__name__, message)
    orig_fmt = warnings.formatwarning
    warnings.formatwarning = formatwarning
    warnings.warn(ClientModeWarning())
    warnings.formatwarning = orig_fmt

if RTLSDR_CLIENT_MODE:
    warn_client_mode()
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
