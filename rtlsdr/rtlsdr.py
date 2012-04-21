from __future__ import division
from librtlsdr import librtlsdr, p_rtlsdr_dev, rtlsdr_read_async_cb_t
from ctypes import *
from functools import wraps
import time

class BaseRtlSdr(object):
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
        gain = int(gain)
        
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
        num_bytes = 2*num_samples
        
        raw_data = self.read_bytes(num_bytes)
        iq = self.packed_bytes_to_iq(raw_data)
        
        return iq

    def packed_bytes_to_iq(self, bytes):
        # TODO: use NumPy for this
        iq = [complex(i/255, q/255) for i, q in zip(bytes[::2], bytes[1::2])]

        return iq
    
    center_freq = fc = property(get_center_freq, set_center_freq)
    sample_rate = rs = property(get_sample_rate, set_sample_rate)
    gain = property(get_gain, set_gain)

class RtlSdr(BaseRtlSdr):
    DEFAULT_ASYNC_BUF_NUMBER = 32
    DEFAULT_READ_SIZE = 1024
    
    read_async_canceling = False

    def read_bytes_async(self, callback, num_bytes=DEFAULT_READ_SIZE, context=None):
        '''Continuously read "num_bytes" bytes from tuner and call Python function
        "callback" with the result. "context" is any Python object that will be
        make available to callback function (default supplies this RtlSdr object).
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
        values = array_type.from_address(addressof(raw_buffer))
        
        self._callback_bytes(values, context)

    def read_samples_async(self, callback, num_samples=DEFAULT_READ_SIZE, context=None):
        '''Same as read_bytes_async() but unpacks bytes into a list of complex
        numbers.
        '''
        num_bytes = 2*num_samples
        
        self._callback_samples = callback        
        self.read_bytes_async(self._samples_converter_callback, num_bytes, context)
        
        return
    
    def _samples_converter_callback(self, buffer, context):
        iq = self.packed_bytes_to_iq(buffer)
        
        self._callback_samples(iq, context)
    
    def cancel_read_async(self):       
        '''Cancel async read. See also decorators limit_time() and limit_calls()'''

        result = librtlsdr.rtlsdr_cancel_async(self.dev_p)
        # sometimes we get additional callbacks after canceling an async read,
        # in this case we don't raise exceptions
        if result < 0 and not self.read_async_canceling:
            self.close()
            raise IOError('Error code %d when canceling async read'\
                          % (result))
            
        self.read_async_canceling = True
    

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
            if elapsed > max_seconds:
                rtlsdr_obj.cancel_read_async()
                return
            
            return f(buffer, rtlsdr_obj)

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

            if f._num_calls > max_calls:
                rtlsdr_obj.cancel_read_async()
                return
            
            return f(buffer, rtlsdr_obj)

        return wrapper
    return decorator

@limit_calls(5)
def test_callback(buffer, rtlsdr_obj):
    print 'In callback'
    print '\tsignal mean:', sum(buffer)/len(buffer)
    
def main():            
    sdr = RtlSdr()
    
    print 'Configuring SDR...'
    sdr.rs = 2e6
    sdr.fc = 70e6
    sdr.gain = 5
    print '\tsample rate: %0.6f MHz' % (sdr.rs/1e6)
    print '\tcenter ferquency %0.6f MHz' % (sdr.fc/1e6)
    print '\tgain: %d dB' % sdr.gain

    print 'Reading samples...'    
    samples = sdr.read_samples(1024)
    print '\tsignal mean:', sum(samples)/len(samples)
    
    print 'Testing callback...'
    sdr.read_samples_async(test_callback)
    
if __name__ == '__main__':
    main()