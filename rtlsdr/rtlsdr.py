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
from ctypes import *
from .librtlsdr import (
    librtlsdr,
    p_rtlsdr_dev,
    rtlsdr_read_async_cb_t,
    tuner_bandwidth_supported,
    tuner_set_bandwidth_supported,
)
try:                from itertools import izip
except ImportError: izip = zip
import sys

PY3 = sys.version_info.major >= 3
if PY3:
    basestring = str

# see if NumPy is available
has_numpy = True
try:
    import numpy as np
except ImportError:
    has_numpy = False


class BaseRtlSdr(object):
    """Core interface for most API functionality

    Arguments:
        device_index (:obj:`int`, optional): The device index to use if there are
            multiple dongles attached.  If only one is being used,
            the default value (0) will be used.
        test_mode_enabled (:obj:`bool`, optional): If True, enables a special
            test mode, which will return the value of an internal RTL2832
            8-bit counter with calls to :meth:`read_bytes`.
        serial_number (:obj:`str`, optional): If not None, the device will be searched
            for by the given serial_number by :meth:`get_device_index_by_serial`
            and the ``device_index`` returned will be used automatically.

    Attributes:
        DEFAULT_GAIN: Default :attr:`gain` value used on initialization: ``'auto'``
        DEFAULT_FC (float): Default :attr:`center_freq` value used on
            initialization: ``80e6`` (80 Mhz)
        DEFAULT_RS (float): Default :attr:`sample_rate` value used on
            initialization: ``1.024e6`` (1024 Msps)
        DEFAULT_READ_SIZE (int): Default number of samples or bytes to read
            if no arguments are supplied for :meth:`read_bytes`
            or :meth:`read_samples`.  Default value is ``1024``
        gain_values (list(int)): The valid gain parameters supported by the device
            (in tenths of dB). These are stored as returned by ``librtlsdr``.
        valid_gains_db (list(float)): The valid gains in dB

    """
    # some default values for various parameters
    DEFAULT_GAIN = 'auto'
    DEFAULT_FC = 80e6
    DEFAULT_RS = 1.024e6
    DEFAULT_READ_SIZE = 1024

    CRYSTAL_FREQ = 28800000

    gain_values = []
    valid_gains_db = []
    buffer = []
    num_bytes_read = c_int32(0)
    device_opened = False

    @staticmethod
    def get_device_index_by_serial(serial):
        """Retrieves the device index for a device matching the given serial number

        Arguments:
            serial (str): The serial number to search for

        Returns:
            int: The device_index as reported by ``librtlsdr``

        Notes:
            Most devices by default have the same serial number: `'0000001'`.
            This can be set to a custom value by using the `rtl\_eeprom`_ utility
            packaged with ``librtlsdr``.

        .. _rtl\_eeprom: http://manpages.ubuntu.com/manpages/trusty/man1/rtl_eeprom.1.html

        """
        if PY3 and isinstance(serial, str):
            serial = bytes(serial, 'UTF-8')

        result = librtlsdr.rtlsdr_get_index_by_serial(serial)
        if result < 0:
            raise LibUSBError(result)

        return result

    @staticmethod
    def get_device_serial_addresses():
        """Get serial numbers for all attached devices

        Returns:
            list(str): A ``list`` of all detected serial numbers (``str``)

        """
        def get_serial(device_index):
            bfr = (c_ubyte * 256)()
            r = librtlsdr.rtlsdr_get_device_usb_strings(device_index, None, None, bfr)
            if r != 0:
                raise LibUSBError(
                    r, 'while reading USB strings (device %d)' % (device_index)
                )
            return ''.join((chr(b) for b in bfr if b > 0))

        num_devices = librtlsdr.rtlsdr_get_device_count()
        return [get_serial(i) for i in range(num_devices)]

    def __init__(self, device_index=0, test_mode_enabled=False, serial_number=None):
        self.open(device_index, test_mode_enabled, serial_number)

    def open(self, device_index=0, test_mode_enabled=False, serial_number=None):
        """Connect to the device through the underlying wrapper library

        Initializes communication with the device and retrieves information
        from it with a call to :meth:`init_device_values`.

        Arguments:
            device_index (:obj:`int`, optional): The device index to use if there are
                multiple dongles attached.  If only one is being used,
                the default value (0) will be used.
            test_mode_enabled (:obj:`bool`, optional): If True, enables a special
                test mode, which will return the value of an internal RTL2832
                8-bit counter with calls to :meth:`read_bytes`.
            serial_number (:obj:`str`, optional): If not None, the device will be searched
                for by the given serial_number by :meth:`get_device_index_by_serial`
                and the ``device_index`` returned will be used automatically.

        Notes:
            The arguments used here are passed directly from object
            initialization.

        Raises:
            IOError: If communication with the device could not be established.

        """

        if serial_number is not None:
            device_index = self.get_device_index_by_serial(serial_number)

        # this is the pointer to the device structure used by all librtlsdr
        # functions
        self.dev_p = p_rtlsdr_dev(None)

        # initialize device
        result = librtlsdr.rtlsdr_open(self.dev_p, device_index)
        if result < 0:
            raise LibUSBError(result, 'Could not open SDR (device index = %d)' % (device_index))

        # enable test mode if necessary
        result = librtlsdr.rtlsdr_set_testmode(self.dev_p, int(test_mode_enabled))
        if result < 0:
            raise LibUSBError(result, 'Could not set test mode')

        # reset buffers
        result = librtlsdr.rtlsdr_reset_buffer(self.dev_p)
        if result < 0:
            raise LibUSBError(result, 'Could not reset buffer')

        self.device_opened = True
        self.init_device_values()

    def init_device_values(self):
        """Retrieves information from the device

        This method acquires the values for :attr:`gain_values`. Also sets the
        device to the default :attr:`center frequency <DEFAULT_FC>`, the
        :attr:`sample rate <DEFAULT_RS>` and :attr:`gain <DEFAULT_GAIN>`
        """
        self.gain_values = self.get_gains()
        self.valid_gains_db = [val/10 for val in self.gain_values]

        # set default state
        self.set_sample_rate(self.DEFAULT_RS)
        self.set_center_freq(self.DEFAULT_FC)
        self.set_gain(self.DEFAULT_GAIN)

    def close(self):
        if not self.device_opened:
            return

        librtlsdr.rtlsdr_close(self.dev_p)
        self.device_opened = False

    def __del__(self):
        self.close()

    def set_center_freq(self, freq):

        freq = int(freq)

        result = librtlsdr.rtlsdr_set_center_freq(self.dev_p, freq)
        if result < 0:
            self.close()
            raise LibUSBError(result, 'Could not set center_freq to %d Hz' % (freq))

        return

    def get_center_freq(self):

        result = librtlsdr.rtlsdr_get_center_freq(self.dev_p)
        if result < 0:
            self.close()
            raise LibUSBError(result, 'Could not get center_freq')

        # FIXME: the E4000 rounds to kHz, this may not be true for other tuners
        reported_center_freq = result
        center_freq = round(reported_center_freq, -3)

        return center_freq

    def set_freq_correction(self, err_ppm):

        freq = int(err_ppm)

        result = librtlsdr.rtlsdr_set_freq_correction(self.dev_p, err_ppm)
        if result < 0:
            self.close()
            raise LibUSBError(result, 'Could not set freq. offset to %d ppm' % (err_ppm))

        return

    def get_freq_correction(self):

        result = librtlsdr.rtlsdr_get_freq_correction(self.dev_p)
        if result < 0:
            self.close()
            raise LibUSBError(result, 'Could not get freq. offset')
        return result

    def set_sample_rate(self, rate):

        rate = int(rate)

        result = librtlsdr.rtlsdr_set_sample_rate(self.dev_p, rate)
        if result < 0:
            self.close()
            raise LibUSBError(result, 'Could not set sample rate to %d Hz' % (rate))

        return

    def get_sample_rate(self):

        result = librtlsdr.rtlsdr_get_sample_rate(self.dev_p)
        if result < 0:
            self.close()
            raise LibUSBError(result, 'Could not get sample rate')

        # figure out actual sample rate, taken directly from librtlsdr
        reported_sample_rate = result
        rsamp_ratio = (self.CRYSTAL_FREQ * pow(2, 22)) // reported_sample_rate
        rsamp_ratio &= ~3
        real_rate = (self.CRYSTAL_FREQ * pow(2, 22)) / rsamp_ratio;

        return real_rate

    def set_bandwidth(self, bw):

        requested_bw = int(bw)
        bw = int(bw)
        if tuner_bandwidth_supported:
            apply_bw = c_int(1)
            applied_bw = c_uint32(bw)
            bw = c_uint32(bw)
            result = librtlsdr.rtlsdr_set_and_get_tuner_bandwidth(
                self.dev_p, bw, byref(applied_bw), apply_bw)
            self._bandwidth = applied_bw.value
        elif tuner_set_bandwidth_supported:
            bw = int(bw)
            result = librtlsdr.rtlsdr_set_tuner_bandwidth(self.dev_p, bw)
            self._bandwidth = bw
        else:
            raise IOError('set_tuner_bandwidth not supported in this version of librtlsdr')

        if result != 0:
            self.close()
            raise LibUSBError(result, 'Could not set tuner bandwidth to %d Hz' % (requested_bw))

        return

    def get_bandwidth(self):

        return getattr(self, '_bandwidth', 0)

    def set_gain(self, gain):
        if isinstance(gain, basestring) and gain == 'auto':
            # disable manual gain -> enable AGC
            self.set_manual_gain_enabled(False)

            return

        # find supported gain nearest to one requested
        errors = [abs(10*gain - g) for g in self.gain_values]
        nearest_gain_ind = errors.index(min(errors))

        # disable AGC
        self.set_manual_gain_enabled(True)

        result = librtlsdr.rtlsdr_set_tuner_gain(self.dev_p,
                                                 self.gain_values[nearest_gain_ind])
        if result < 0:
            self.close()
            raise LibUSBError(result, 'Could not set gain to %d' % (gain))

        return

    def get_gain(self):

        result = librtlsdr.rtlsdr_get_tuner_gain(self.dev_p)
        if 0 and result == 0:
            self.close()
            raise IOError('Error when getting gain')

        return result/10

    def get_gains(self):
        """Get all supported gain values from driver

        Returns:
            list(int): Gains in tenths of a dB
        """
        buffer = (c_int *50)()
        result = librtlsdr.rtlsdr_get_tuner_gains(self.dev_p, buffer)
        if result == 0:
            self.close()
            raise IOError('Error when getting gains')

        gains = []
        for i in range(result):
            gains.append(buffer[i])

        return gains

    def set_manual_gain_enabled(self, enabled):
        """Enable or disable manual gain control of tuner.

        Arguments:
            enabled (bool):

        Notes:
            If ``enabled`` is False, then AGC should also be used by calling
            :meth:`set_agc_mode`. It is recommended to use :meth:`set_gain`
            instead of calling this method directly.
        """
        result = librtlsdr.rtlsdr_set_tuner_gain_mode(self.dev_p, int(enabled))
        if result < 0:
            raise LibUSBError(result, 'Could not get gain mode')

        return

    def set_agc_mode(self, enabled):
        """Enable RTL2832 AGC

        Arguments:
            enabled (bool):
        """
        result = librtlsdr.rtlsdr_set_agc_mode(self.dev_p, int(enabled))
        if result < 0:
            raise LibUSBError(result, 'Could not set AGC mode')

        return result

    def set_bias_tee(self, enabled):
        """Enable RTL2832 Bias Tee

        Enables or disables the Bias Tee option (RTL-SDRv3 only)

        Arguments:
            enabled (bool):

        .. warning::

            Using this could potentially damage your device!
            Please make sure you understand what Bias Tee does before using
            this method.

            See the Bias T section of the `RTL-SDRv3 Manual`_ for information.

        .. versionadded:: 0.2.93

        .. _RTL-SDRv3 Manual: https://www.rtl-sdr.com/rtl-sdr-blog-v-3-dongles-user-guide/
        """
        result = librtlsdr.rtlsdr_set_bias_tee(self.dev_p, int(enabled))
        if result < 0:
            raise LibUSBError(result, 'Could not set Bias Tee mode')

        return result


    def set_direct_sampling(self, direct):
        """Enable direct sampling.

        Arguments:
            direct: If False or 0, disable direct sampling.  If 'i' or 1,
                use ADC I input.  If 'q' or 2, use ADC Q input.
        """

        # convert parameter
        if isinstance(direct, basestring):
            if direct.lower() == 'i':
                direct = 1
            elif direct.lower() == 'q':
                direct = 2
            else:
                raise SyntaxError('invalid value "%s"' % direct)

        # make sure False works as an option
        if not direct:
            direct = 0

        result = librtlsdr.rtlsdr_set_direct_sampling(self.dev_p, direct)
        if result < 0:
            raise LibUSBError(result, 'Could not set direct sampling')

        return result

    def get_tuner_type(self):
        """Get the tuner type.

        Returns:
            int:
                The tuner type as reported by the driver.
                See the `tuner enum definition`_ for more information.

        .. _tuner enum definition: https://github.com/librtlsdr/librtlsdr/blob/c7d970ac5b70e897501909a48b2b32d4bfb16979/include/rtl-sdr.h#L185-L201
        """
        result = librtlsdr.rtlsdr_get_tuner_type(self.dev_p)
        if result < 0:
            raise LibUSBError(result, 'Could not get tuner type')

        return result

    def read_bytes(self, num_bytes=DEFAULT_READ_SIZE):
        """Read specified number of bytes from tuner.

        Does not attempt to unpack complex samples (see :meth:`read_samples`),
        and data may be unsafe as buffer is reused.

        Arguments:
            num_bytes (:obj:`int`, optional): The number of bytes to read.
                Defaults to :attr:`DEFAULT_READ_SIZE`.

        Returns:
            ctypes.Array[c_ubyte]:
                A buffer of len(num_bytes) containing the raw samples read.
        """
        # FIXME: libsdrrtl may not be able to read an arbitrary number of bytes

        num_bytes = int(num_bytes)

        # create buffer, as necessary
        if len(self.buffer) != num_bytes:
            array_type = (c_ubyte*num_bytes)
            self.buffer = array_type()

        result = librtlsdr.rtlsdr_read_sync(self.dev_p, self.buffer, num_bytes,\
                                            byref(self.num_bytes_read))
        if result < 0:
            self.close()
            raise LibUSBError(result, 'Could not read %d bytes' % (num_bytes))

        if self.num_bytes_read.value != num_bytes:
            self.close()
            raise IOError('Short read, requested %d bytes, received %d'\
                          % (num_bytes, self.num_bytes_read.value))

        return self.buffer

    def read_samples(self, num_samples=DEFAULT_READ_SIZE):
        """Read specified number of complex samples from tuner.

        Real and imaginary parts are normalized to be in the range [-1, 1].
        Data is safe after this call (will not get overwritten by another one).

        Arguments:
            num_samples (:obj:`int`, optional): Number of samples to read.
                Defaults to :attr:`DEFAULT_READ_SIZE`.

        Returns:
            The samples read as either a :class:`list` or :class:`numpy.ndarray`
            (if available).
        """
        num_bytes = 2*num_samples

        raw_data = self.read_bytes(num_bytes)
        iq = self.packed_bytes_to_iq(raw_data)

        return iq

    def packed_bytes_to_iq(self, bytes):
        """Unpack a sequence of bytes to a sequence of normalized complex numbers

        This is called automatically by :meth:`read_samples`.

        Returns:
            The unpacked iq values as either a :class:`list` or
            :class:`numpy.ndarray` (if available).
        """
        if has_numpy:
            # use NumPy array
            data = np.ctypeslib.as_array(bytes)
            iq = data.astype(np.float64).view(np.complex128)
            iq /= 127.5
            iq -= (1 + 1j)
        else:
            # use normal list
            iq = [complex(i/(255/2) - 1, q/(255/2) - 1) for i, q in izip(bytes[::2], bytes[1::2])]

        return iq

    center_freq = fc = property(get_center_freq, set_center_freq,
        doc="""int: Get/Set the center frequency of the device (in Hz)""")
    sample_rate = rs = property(get_sample_rate, set_sample_rate,
        doc="""int: Get/Set the sample rate of the tuner (in Hz)""")
    gain = property(get_gain, set_gain,
        doc="""float or str: Get/Set gain of the tuner (in dB)

        Notes:
            If set to 'auto', AGC mode is enabled; otherwise gain is in dB.
            The actual gain used is rounded to the nearest value supported by
            the device (see the values in :attr:`valid_gains_db`).
        """)
    freq_correction = property(get_freq_correction, set_freq_correction,
        doc="""int: Get/Set frequency offset of the tuner (in PPM)""")
    bandwidth = property(get_bandwidth, set_bandwidth,
        doc="""int: Get/Set bandwidth value (in Hz)

        Set value to 0 (default) for automatic bandwidth selection.

        Notes:
            This value is stored locally and may not reflect the real tuner bandwidth

        """)


# This adds async read support to base class BaseRtlSdr (don't use that one)
class RtlSdr(BaseRtlSdr):
    """This adds async read support to :class:`BaseRtlSdr`
    """
    DEFAULT_ASYNC_BUF_NUMBER = 0 # librtlsdr will use the default (15)
    DEFAULT_READ_SIZE = 1024

    read_async_canceling = False

    def read_bytes_async(self, callback, num_bytes=DEFAULT_READ_SIZE, context=None):
        """Continuously read bytes from tuner

        Arguments:
            callback: A function or method that will be called with the result.
                See :meth:`_bytes_converter_callback` for the signature.
            num_bytes (int): Number of bytes to read for each callback.
                Defaults to :attr:`DEFAULT_READ_SIZE`.
            context (Optional): Object to be passed as an argument to the callback.
                If not supplied or None, the :class:`RtlSdr` instance
                will be used.

        Notes:
            As with :meth:`~BaseRtlSdr.read_bytes`, the data passed to the
            callback may by overwritten.
        """
        num_bytes = int(num_bytes)

        # we don't call the provided callback directly, but add a layer inbetween
        # to convert the raw buffer to a safer type

        # save requested callback
        self._callback_bytes = callback

        # convert Python callback function to a librtlsdr callback
        rtlsdr_callback = rtlsdr_read_async_cb_t(self._bytes_converter_callback)

        # use this object as context if none provided
        if not context:
            context = self

        self.read_async_canceling = False
        result = librtlsdr.rtlsdr_read_async(self.dev_p, rtlsdr_callback,\
                    context, self.DEFAULT_ASYNC_BUF_NUMBER, num_bytes)
        if result < 0:
            self.close()
            raise LibUSBError(result, 'Could not read %d bytes' % (num_bytes))

        self.read_async_canceling = False

        return

    def _bytes_converter_callback(self, raw_buffer, num_bytes, context):
        """Converts the raw buffer used in ``rtlsdr_read_async`` to a usable type

        This method is used internally by :meth:`read_bytes_async` to convert
        the raw data from ``rtlsdr_read_async`` into a memory-safe array.

        The callback given in :meth:`read_bytes_async` will then be called
        with the signature::

            callback(values, context)

        Arguments:
            raw_buffer: Buffer of type ``unsigned char``
            num_bytes (int): Length of ``raw_buffer``
            context: User-defined value passed to ``rtlsdr_read_async``.
                In most cases, will be a reference to the :class:`RtlSdr` instance

        Notes:
            This method is not meant to be called directly or
            overridden by subclasses.

        """
        array_type = (c_ubyte*num_bytes)
        values = cast(raw_buffer, POINTER(array_type)).contents

        # skip callback if cancel_read_async() called
        if self.read_async_canceling:
            return

        self._callback_bytes(values, context)

    def read_samples_async(self, callback, num_samples=DEFAULT_READ_SIZE, context=None):
        """Continuously read 'samples' from the tuner

        This is a combination of :meth:`read_samples` and :meth:`read_bytes_async`

        Arguments:
            callback: A function or method that will be called with the result.
                See :meth:`_samples_converter_callback` for the signature.
            num_samples (int): The number of samples read into each callback.
                Defaults to :attr:`DEFAULT_READ_SIZE`.
            context (Optional): Object to be passed as an argument to the callback.
                If not supplied or None, the :class:`RtlSdr` instance
                will be used.
        """

        num_bytes = 2*num_samples

        self._callback_samples = callback
        self.read_bytes_async(self._samples_converter_callback, num_bytes, context)

        return

    def _samples_converter_callback(self, buffer, context):
        """Converts the raw buffer used in ``rtlsdr_read_async`` to a usable type

        This method is used internally by :meth:`read_samples_async` to convert
        the data into a sequence of complex numbers.

        The callback given in :meth:`read_samples_async` will then be called
        with the signature::

            callback(samples, context)

        Arguments:
            buffer: Buffer of type ``unsigned char``
            context: User-defined value passed to ``rtlsdr_read_async``.
                In most cases, will be a reference to the :class:`RtlSdr` instance

        Notes:
            This method is not meant to be called directly or
            overridden by subclasses.

        """
        iq = self.packed_bytes_to_iq(buffer)

        self._callback_samples(iq, context)

    def cancel_read_async(self):
        """Cancel async read.
        This should be called eventually when using async reads
        (:meth:`read_bytes_async` or :meth:`read_samples_async`),
        or callbacks will never stop.

        See Also:
            :func:`~rtlsdr.helpers.limit_time` and
            :func:`~rtlsdr.helpers.limit_calls`
        """

        result = librtlsdr.rtlsdr_cancel_async(self.dev_p)
        # sometimes we get additional callbacks after canceling an async read,
        # in this case we don't raise exceptions
        if result < 0 and not self.read_async_canceling:
            self.close()
            raise LibUSBError(result, 'Could not cancel async read')

        self.read_async_canceling = True


class LibUSBError(IOError):
    _errno_map = {
        -1:  ('LIBUSB_ERROR_IO', 'Input/output error'),
        -2:  ('LIBUSB_ERROR_INVALID_PARAM', 'Invalid parameter'),
        -3:  ('LIBUSB_ERROR_ACCESS', 'Access denied (insufficient permissions)'),
        -4:  ('LIBUSB_ERROR_NO_DEVICE', 'No such device (it may have been disconnected)'),
        -5:  ('LIBUSB_ERROR_NOT_FOUND', 'Entity not found'),
        -6:  ('LIBUSB_ERROR_BUSY', 'Resource busy'),
        -7:  ('LIBUSB_ERROR_TIMEOUT', 'Operation timed out'),
        -8:  ('LIBUSB_ERROR_OVERFLOW', 'Overflow'),
        -9:  ('LIBUSB_ERROR_PIPE', 'Pipe error'),
        -10: ('LIBUSB_ERROR_INTERRUPTED', 'System call interrupted (perhaps due to signal)'),
        -11: ('LIBUSB_ERROR_NO_MEM', 'Insufficient memory'),
        -12: ('LIBUSB_ERROR_NOT_SUPPORTED', 'Operation not supported or unimplemented on this platform'),
        -99: ('LIBUSB_ERROR_OTHER', 'Other error'),
    }
    def __init__(self, errno, msg=''):
        self.errno = errno
        self.msg = msg
    def __str__(self):
        t = self._errno_map.get(self.errno)
        if t is not None:
            err_id, err_msg = t
            msg = '<{err_id} ({self.errno}): {err_msg}> "{self.msg}"'.format(
                self=self, err_id=err_id, err_msg=err_msg,
            )
        else:
            msg = 'Error code {self.errno}: {self.msg}'.format(self=self)
        return msg
