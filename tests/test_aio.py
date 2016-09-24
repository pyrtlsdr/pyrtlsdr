import asyncio

def test(rtlsdraio):
    async def main():
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

        print('Streaming samples...')

        i = 0
        async for samples in sdr.stream():
            power = sum(abs(s)**2 for s in samples) / len(samples)
            print('Relative power:', 10*math.log10(power), 'dB')

            i += 1

            if i > 20:
                await sdr.stop()
                break

        print('Done')

        sdr.close()

    async def do_nothing():
        for i in range(50):
            await asyncio.sleep(0.1)
            print('#')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([main(), do_nothing()]))
