from __future__ import division
from rtlsdr import *

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