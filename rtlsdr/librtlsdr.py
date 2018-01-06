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


import sys
import os
from ctypes import *
from ctypes.util import find_library

def load_librtlsdr():
    if sys.platform == "linux" and 'LD_LIBRARY_PATH' in os.environ.keys():
        ld_library_paths = [local_path for local_path in os.environ['LD_LIBRARY_PATH'].split(':') if local_path.strip()]
        driver_files = [local_path + '/librtlsdr.so' for local_path in ld_library_paths]
    else:
        driver_files = []
    driver_files += ['librtlsdr.so', 'rtlsdr/librtlsdr.so']
    driver_files += ['rtlsdr.dll', 'librtlsdr.so']
    driver_files += ['..//rtlsdr.dll', '..//librtlsdr.so']
    driver_files += ['rtlsdr//rtlsdr.dll', 'rtlsdr//librtlsdr.so']
    driver_files += [lambda : find_library('rtlsdr'), lambda : find_library('librtlsdr')]
    dll = None

    for driver in driver_files:
        if callable(driver):
            driver = driver()
        try:
            dll = CDLL(driver)
            break
        except:
            pass
    else:
        raise ImportError('Error loading librtlsdr. Make sure librtlsdr '\
                          '(and all of its dependencies) are in your path')

    return dll

librtlsdr = load_librtlsdr()

# we don't care about the rtlsdr_dev struct and it's allocated by librtlsdr, so
# we won't even bother filling it in
p_rtlsdr_dev = c_void_p

# async callbacks must be passed through this function
# typedef void(*rtlsdr_read_async_cb_t)(unsigned char *buf, uint32_t len, void *ctx);
rtlsdr_read_async_cb_t = CFUNCTYPE(None, POINTER(c_ubyte), c_int, py_object)

# uint32_t rtlsdr_get_device_count(void);
f = librtlsdr.rtlsdr_get_device_count
f.restype, f.argtypes = c_uint, []

# const char* rtlsdr_get_device_name(uint32_t index);
f = librtlsdr.rtlsdr_get_device_name
f.restype, f.argtypes = c_char_p, [c_uint]

# int rtlsdr_get_device_usb_strings(uint32_t index, char *manufact,
#                                   char *product, char *serial)
f = librtlsdr.rtlsdr_get_device_usb_strings
f.restype, f.argtypes = c_int, [c_uint,
                                POINTER(c_ubyte),
                                POINTER(c_ubyte),
                                POINTER(c_ubyte)]

# int rtlsdr_get_index_by_serial(const char *serial);
f = librtlsdr.rtlsdr_get_index_by_serial
f.restype, f.argtypes = c_int, [c_char_p]

# int rtlsdr_open(rtlsdr_dev_t **dev, uint32_t index);
f = librtlsdr.rtlsdr_open
f.restype, f.argtypes = c_int, [POINTER(p_rtlsdr_dev), c_uint]

# int rtlsdr_close(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_close
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# /* configuration functions */

# int rtlsdr_set_center_freq(rtlsdr_dev_t *dev, uint32_t freq);
f = librtlsdr.rtlsdr_set_center_freq
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_uint]

# int rtlsdr_get_center_freq(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_center_freq
f.restype, f.argtypes = c_uint, [p_rtlsdr_dev]

# int rtlsdr_set_freq_correction(rtlsdr_dev_t *dev, int ppm);
f = librtlsdr.rtlsdr_set_freq_correction
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

# int rtlsdr_get_freq_correction(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_freq_correction
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# enum rtlsdr_tuner rtlsdr_get_tuner_type(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_tuner_type
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# int rtlsdr_set_tuner_gain(rtlsdr_dev_t *dev, int gain);
f = librtlsdr.rtlsdr_set_tuner_gain
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

# int rtlsdr_get_tuner_gain(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_tuner_gain
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# int rtlsdr_get_tuner_gains(rtlsdr_dev_t *dev, int *gains)
f = librtlsdr.rtlsdr_get_tuner_gains
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, POINTER(c_int)]

# RTLSDR_API int rtlsdr_set_tuner_gain_mode(rtlsdr_dev_t *dev, int manual);
f = librtlsdr.rtlsdr_set_tuner_gain_mode
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

# RTLSDR_API int rtlsdr_set_agc_mode(rtlsdr_dev_t *dev, int on);
f = librtlsdr.rtlsdr_set_agc_mode
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

# RTLSDR_API  int rtlsdr_set_direct_sampling(rtlsdr_dev_t *dev, int on)
f = librtlsdr.rtlsdr_set_direct_sampling
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]


# int rtlsdr_set_sample_rate(rtlsdr_dev_t *dev, uint32_t rate);
f = librtlsdr.rtlsdr_set_sample_rate
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_uint]

# int rtlsdr_get_sample_rate(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_sample_rate
f.restype, f.argtypes = c_uint, [p_rtlsdr_dev]

# int rtlsdr_set_and_get_tuner_bandwidth(rtlsdr_dev_t *dev, uint32_t bw, uint32_t *applied_bw, int apply_bw );
try:
    f = librtlsdr.rtlsdr_set_and_get_tuner_bandwidth
    f.restype, f.argtypes = c_uint, [p_rtlsdr_dev, c_uint32, POINTER(c_uint32), c_int]
    tuner_bandwidth_supported = True
except AttributeError:
    tuner_bandwidth_supported = False

# int rtlsdr_set_tuner_bandwidth(rtlsdr_dev_t *dev, uint32_t bw);
try:
    f = librtlsdr.rtlsdr_set_tuner_bandwidth
    f.restype, f.argtypes = c_uint, [p_rtlsdr_dev, c_uint]
    tuner_set_bandwidth_supported = True
except AttributeError:
    tuner_set_bandwidth_supported = False

#/* streaming functions */

# int rtlsdr_reset_buffer(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_reset_buffer
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# int rtlsdr_read_sync(rtlsdr_dev_t *dev, void *buf, int len, int *n_read);
f = librtlsdr.rtlsdr_read_sync
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_void_p, c_int, POINTER(c_int)]

# int rtlsdr_wait_async(rtlsdr_dev_t *dev, rtlsdr_read_async_cb_t cb, void *ctx);
f = librtlsdr.rtlsdr_wait_async
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, POINTER(rtlsdr_read_async_cb_t), py_object]

#int rtlsdr_read_async(rtlsdr_dev_t *dev,
#				 rtlsdr_read_async_cb_t cb,
#				 void *ctx,
#				 uint32_t buf_num,
#				 uint32_t buf_len);
f = librtlsdr.rtlsdr_read_async
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, rtlsdr_read_async_cb_t, py_object, c_uint, c_uint]

# int rtlsdr_cancel_async(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_cancel_async
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# RTLSDR_API int rtlsdr_set_xtal_freq(rtlsdr_dev_t *dev, uint32_t rtl_freq,
#				    uint32_t tuner_freq);
f = librtlsdr.rtlsdr_set_xtal_freq
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_uint, c_uint]

# RTLSDR_API int rtlsdr_get_xtal_freq(rtlsdr_dev_t *dev, uint32_t *rtl_freq,
#				    uint32_t *tuner_freq);
f = librtlsdr.rtlsdr_get_xtal_freq
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, POINTER(c_uint), POINTER(c_uint)]

# RTLSDR_API int rtlsdr_set_testmode(rtlsdr_dev_t *dev, int on);
f = librtlsdr.rtlsdr_set_testmode
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

__all__  = ['librtlsdr', 'p_rtlsdr_dev', 'rtlsdr_read_async_cb_t']
