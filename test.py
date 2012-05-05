from __future__ import division
from rtlsdr import *

@limit_calls(2)
def test_callback(samples, rtlsdr_obj):
    print '  in callback'
    print '  signal mean:', sum(samples)/len(samples)

def main():
    sdr = RtlSdr()

    print 'Configuring SDR...'
    sdr.rs = 3e6
    sdr.fc = 100e6
    sdr.gain = -1
    print '  sample rate: %0.6f MHz' % (sdr.rs/1e6)
    print '  center frequency %0.6f MHz' % (sdr.fc/1e6)
    print '  gain: %d dB' % sdr.gain

    print 'Reading samples...'
    samples = sdr.read_samples(500e3)
    print '  signal mean:', sum(samples)/len(samples)

    print 'Testing callback...'
    sdr.read_samples_async(test_callback, 500e3)

    try:
        import pylab as mpl

        print 'Testing spectrum plotting...'
        mpl.figure()
        mpl.psd(samples, NFFT=1024, Fc=sdr.fc/1e6, Fs=sdr.rs/1e6)

        mpl.show()
    except:
        # matplotlib not installed/working
        pass

    print 'Done\n'
    sdr.close()

if __name__ == '__main__':
    main()