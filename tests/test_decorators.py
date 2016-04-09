def test(sdr_cls):
    from rtlsdr import limit_time, limit_calls

    @limit_time(0.01)
    @limit_calls(20)
    def read_callback(buffer, rtlsdr_obj):
        print('In callback')
        print('   signal mean:', sum(buffer)/len(buffer))

    sdr = sdr_cls()

    print('Configuring SDR...')
    sdr.rs = 1e6
    sdr.fc = 70e6
    sdr.gain = 5
    print('   sample rate: %0.6f MHz' % (sdr.rs/1e6))
    print('   center ferquency %0.6f MHz' % (sdr.fc/1e6))
    print('   gain: %d dB' % sdr.gain)

    print('Testing callback...')
    sdr.read_samples_async(read_callback)
    sdr.close()
