import asyncio
import pytest

def test(rtlsdraio):
    import math
    from utils import generic_test

    async def main():
        sdr = rtlsdraio.RtlSdrAio()
        generic_test(sdr)

        print('Configuring SDR...')
        sdr.rs = 2.4e6
        sdr.fc = 100e6
        sdr.gain = 10
        print('  sample rate: %0.6f MHz' % (sdr.rs/1e6))
        print('  center frequency %0.6f MHz' % (sdr.fc/1e6))
        print('  gain: %d dB' % sdr.gain)


        print('Streaming samples...')
        await process_samples(sdr, 'samples')
        await sdr.stop()

        print('Streaming bytes...')
        await process_samples(sdr, 'bytes')
        await sdr.stop()

        # make sure our format parameter checks work
        with pytest.raises(ValueError):
            await process_samples(sdr, 'foo')

        print('Done')

        sdr.close()


    async def process_samples(sdr, fmt):
        async def packed_bytes_to_iq(samples):
            return sdr.packed_bytes_to_iq(samples)

        i = 0
        async for samples in sdr.stream(format=fmt):
            if fmt == 'bytes':
                samples = await packed_bytes_to_iq(samples)
            power = sum(abs(s)**2 for s in samples) / len(samples)
            print('Relative power:', 10*math.log10(power), 'dB')

            i += 1

            if i > 20:
                break

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
