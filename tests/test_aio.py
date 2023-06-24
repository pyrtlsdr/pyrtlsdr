import pytest

@pytest.fixture(params=['samples', 'bytes'])
def read_format(request):
    return request.param

@pytest.mark.asyncio
async def test(rtlsdraio, read_format):
    import math
    from utils import generic_test

    sdr = rtlsdraio.RtlSdrAio()
    generic_test(sdr)

    print('Configuring SDR...')
    sdr.rs = 2.4e6
    sdr.fc = 100e6
    sdr.gain = 10
    print('  sample rate: %0.6f MHz' % (sdr.rs/1e6))
    print('  center frequency %0.6f MHz' % (sdr.fc/1e6))
    print('  gain: %d dB' % sdr.gain)


    print('Streaming %s...' % (read_format))

    i = 0
    async_iter = sdr.stream(format=read_format)
    async for samples in async_iter:
        if read_format == 'bytes':
            samples = sdr.packed_bytes_to_iq(samples)
        power = sum(abs(s)**2 for s in samples) / len(samples)
        print('Relative power:', 10*math.log10(power), 'dB')

        i += 1

        if i > 20:
            break
    await sdr.stop()

    assert not async_iter.running
    assert async_iter.executor_task.done()

    # make sure our format parameter checks work
    with pytest.raises(ValueError):
        _ = sdr.stream(format='foo')

    print('Done')

    sdr.close()
