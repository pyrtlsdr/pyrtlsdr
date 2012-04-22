from __future__ import division
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
    from rtlsdr import RtlSdr
             
    sdr = RtlSdr()
    
    print 'Configuring SDR...'
    sdr.rs = 2e6
    sdr.fc = 70e6
    sdr.gain = 5
    print '\tsample rate: %0.6f MHz' % (sdr.rs/1e6)
    print '\tcenter ferquency %0.6f MHz' % (sdr.fc/1e6)
    print '\tgain: %d dB' % sdr.gain
    
    print 'Testing callback...'
    sdr.read_samples_async(test_callback)
    
if __name__ == '__main__':
    main()