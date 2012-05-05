from __future__ import division
from ctypes import *
from librtlsdr import librtlsdr, p_rtlsdr_dev, rtlsdr_read_async_cb_t
from itertools import izip

# see if NumPy is available
has_numpy = True
try:
    import numpy as np
except ImportError:
    has_numpy = False
    
class BaseRtlSdr(object):
    #Gain values in tenths of a dB
    GAIN_VALUES = [-10, 15, 40, 65, 90, 115, 140, 165, 190, \
        215, 240, 290, 340, 420, 430, 450, 470, 490]
    DEFAULT_GAIN = 1
    DEFAULT_FC = 80e6
    DEFAULT_RS = 1e6
    DEFAULT_READ_SIZE = 1024
    CRYSTAL_FREQ = 28800000

    buffer = []
    num_bytes_read = c_int32(0)
    device_opened = False
    
    def __init__(self, device_index=0):
        # initialize device
        self.dev_p = p_rtlsdr_dev(None)
        
        result = librtlsdr.rtlsdr_open(self.dev_p, device_index)
        if result < 0:
            raise IOError('Error code %d when opening SDR (device index = %d)'\
                          % (result, device_index))
            
        result = librtlsdr.rtlsdr_reset_buffer(self.dev_p)
        if result < 0:
            raise IOError('Error code %d when resetting buffer (device index = %d)'\
                          % (result, device_index))
            
        self.device_opened = True
        
        # set default state
        self.set_sample_rate(self.DEFAULT_RS)
        self.set_center_freq(self.DEFAULT_FC)
        self.manual_gain_mode = False
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
            raise IOError('Error code %d when setting center freq. to %d Hz'\
                          % (result, freq))

        return
    
    def get_center_freq(self):
        result = librtlsdr.rtlsdr_get_center_freq(self.dev_p)        
        if result < 0:
            self.close()
            raise IOError('Error code %d when getting center freq.'\
                          % (result))

        # FIXME: the E4000 rounds to kHz, this may not be true for other tuners
        reported_center_freq = result
        center_freq = round(reported_center_freq, -3)
        
        return center_freq
    
    def get_gain_mode(self):
        return self.manual_gain_mode
    
    def set_gain_mode(self, manual):
        manual = int(manual)
        
        result = librtlsdr.rtlsdr_set_tuner_gain_mode(self.dev_p, manual)        
        if result < 0:
            self.close()
            raise IOError('Error code %d when setting gain mode rate to %d'\
                          % (result, manual))
        
        self.manual_gain_mode = manual != 0
        return
        
    def set_sample_rate(self, rate):
        rate = int(rate)
        
        result = librtlsdr.rtlsdr_set_sample_rate(self.dev_p, rate)        
        if result < 0:
            self.close()
            raise IOError('Error code %d when setting sample rate to %d Hz'\
                          % (result, freq))

        return
    
    def get_sample_rate(self):
        result = librtlsdr.rtlsdr_get_sample_rate(self.dev_p)        
        if result < 0:
            self.close()
            raise IOError('Error code %d when getting sample rate'\
                          % (result))            
            
        # figure out actual sample rate, taken directly from librtlsdr
        reported_sample_rate = result
        rsamp_ratio = (self.CRYSTAL_FREQ * pow(2, 22)) // reported_sample_rate
        rsamp_ratio &= ~3
        real_rate = (self.CRYSTAL_FREQ * pow(2, 22)) / rsamp_ratio;

        return real_rate
        
    def set_gain(self, gain):
        gain = self.GAIN_VALUES[int(gain)]
        
        if not self.manual_gain_mode:
            self.set_gain_mode(True)
        
        result = librtlsdr.rtlsdr_set_tuner_gain(self.dev_p, gain)        
        if result < 0:
            self.close()
            raise IOError('Error code %d when setting gain to %d'\
                          % (result, gain))

        return
    
    def get_gain(self):
        result = librtlsdr.rtlsdr_get_tuner_gain(self.dev_p)        
        if result < 0:
            self.close()
            raise IOError('Error code %d when getting gain'\
                          % (result))

        return result
    
    def read_bytes(self, num_bytes=DEFAULT_READ_SIZE):
        ''' Read specified number of bytes from tuner. Does not attempt to unpack
        complex samples (see read_samples()), and data may be unsafe as buffer is
        reused.
        '''
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
            raise IOError('Error code %d when reading %d bytes'\
                          % (result, num_bytes))
                          
        if self.num_bytes_read.value != num_bytes:
            self.close()
            raise IOError('Short read, requested %d bytes, received %d'\
                          % (num_bytes, self.num_bytes_read.value))
            
        return self.buffer
    
    def read_samples(self, num_samples=DEFAULT_READ_SIZE):
        ''' Read specified number of complex samples from tuner. Real and imaginary
        parts are normalized to be in the range [-1, 1]. Data is safe after
        this call (will not get overwritten by another one).
        '''
        num_bytes = 2*num_samples
        
        raw_data = self.read_bytes(num_bytes)
        iq = self.packed_bytes_to_iq(raw_data)
        
        return iq

    def packed_bytes_to_iq(self, bytes):
        ''' Convenience function to unpack array of bytes to Python list/array
        of complex numbers and normalize range. Called automatically by read_samples()
        '''
        if has_numpy:
            # use NumPy array
            iq = np.empty(len(bytes)//2, 'complex')
            iq.real, iq.imag = bytes[::2], bytes[1::2]
            iq /= (255/2)
            iq -= (1 + 1j)
        else:
            # use normal list
            iq = [complex(i/(255/2) - 1, j/(255/2) - 1) for i, q in izip(bytes[::2], bytes[1::2])]

        return iq
    
    center_freq = fc = property(get_center_freq, set_center_freq)
    sample_rate = rs = property(get_sample_rate, set_sample_rate)
    manual_gain = property(get_gain_mode, set_gain_mode)
    gain = property(get_gain, set_gain)

# This adds async read support to base class BaseRtlSdr (don't use that one)
class RtlSdr(BaseRtlSdr):
    DEFAULT_ASYNC_BUF_NUMBER = 32
    DEFAULT_READ_SIZE = 1024
    
    read_async_canceling = False

    def read_bytes_async(self, callback, num_bytes=DEFAULT_READ_SIZE, context=None):
        ''' Continuously read "num_bytes" bytes from tuner and call Python function
        "callback" with the result. "context" is any Python object that will be
        make available to callback function (default supplies this RtlSdr object).
        Data may be overwritten (see read_bytes())
        '''
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
            raise IOError('Error code %d when requesting %d bytes'\
                          % (result, num_bytes))
            
        self.read_async_canceling = False

        return
    
    def _bytes_converter_callback(self, raw_buffer, num_bytes, context):
        # convert buffer to safer type
        array_type = (c_ubyte*num_bytes)        
        values = cast(raw_buffer, POINTER(array_type)).contents
        
        # skip callback if cancel_read_async() called
        if self.read_async_canceling:
            return
        
        self._callback_bytes(values, context)

    def read_samples_async(self, callback, num_samples=DEFAULT_READ_SIZE, context=None):
        ''' Combination of read_samples() and read_bytes_async() '''
        
        num_bytes = 2*num_samples
        
        self._callback_samples = callback        
        self.read_bytes_async(self._samples_converter_callback, num_bytes, context)
        
        return
    
    def _samples_converter_callback(self, buffer, context):
        iq = self.packed_bytes_to_iq(buffer)
        
        self._callback_samples(iq, context)
    
    def cancel_read_async(self):       
        ''' Cancel async read. This should be called eventually when using async
        reads, or callbacks will never stop. See also decorators limit_time() 
        and limit_calls() in helpers.py.
        '''

        result = librtlsdr.rtlsdr_cancel_async(self.dev_p)
        # sometimes we get additional callbacks after canceling an async read,
        # in this case we don't raise exceptions
        if result < 0 and not self.read_async_canceling:
            self.close()
            raise IOError('Error code %d when canceling async read'\
                          % (result))
            
        self.read_async_canceling = True
    
def test_callback(buffer, rtlsdr_obj):
    print '  in callback'
    print '  signal mean:', sum(buffer)/len(buffer)

    # note we may get additional callbacks even after calling this
    rtlsdr_obj.cancel_read_async()
    
def main():            
    sdr = RtlSdr()
    
    print 'Configuring SDR...'
    sdr.rs = 2e6
    sdr.fc = 70e6
    sdr.gain = 5
    print '  sample rate: %0.6f MHz' % (sdr.rs/1e6)
    print '  center frequency %0.6f MHz' % (sdr.fc/1e6)
    print '  gain: %d dB' % sdr.gain

    print 'Reading samples...'    
    samples = sdr.read_samples(1024)
    print '  signal mean:', sum(samples)/len(samples)
    
    print 'Testing callback...'
    sdr.read_samples_async(test_callback)
    
    sdr.close()
    
if __name__ == '__main__':
    main()