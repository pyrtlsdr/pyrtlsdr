import logging
try:
    import asyncio
    AIO_AVAILABLE = True
except ImportError:
    AIO_AVAILABLE = False
from .rtlsdr import RtlSdr


log = logging.getLogger(__name__)

_CLASS_TEMPLATE = """
class AsyncCallbackIter:
    '''
    Convert a callback-based legacy async function into one supporting asyncio
    and Python 3.5+
    '''

    def __init__(self, func_start, func_stop=None, queue_size=20, *, loop=None):
        '''
        Function `func_start` should take a single callback that will be passed
        data. Will be run in a seperate thread in case it blocks.
        Function `func_stop` is an optional function to stop `func_start` from
        calling the callback. Will be run in a seperate thread in case it blocks.
        `queue_size` is the maximum number of data that will be buffered.
        `loop` is an optional asyncio event loop.
        '''
        self.queue = asyncio.Queue(queue_size)
        self.loop = loop if loop else asyncio.get_event_loop()
        self.func_stop = func_stop
        self.func_start = func_start

        self.running = False

    def _callback(self, *args):
        if self.running and not self.queue.full():
            self.loop.call_soon_threadsafe(self.queue.put_nowait, args)
        else:
            log.info('extra callback data lost')

    def start(self):
        assert(not self.running)

        # start legacy async function
        future = self.loop.run_in_executor(None, self.func_start, self._callback)
        asyncio.ensure_future(future, loop=self.loop)
        self.running = True

    def stop(self):
        assert(self.running)

        # send a signal to stop
        self.queue.put_nowait((StopAsyncIteration(),))
        self.running = False

        if self.func_stop:
            # stop legacy async function
            future = self.loop.run_in_executor(None, self.func_stop)
            asyncio.ensure_future(future, loop=self.loop)

            #self.func_stop()

    async def __aiter__(self):
        return self

    async def __anext__(self):
        val = await self.queue.get()

        if isinstance(val[0], StopAsyncIteration):
            raise StopAsyncIteration

        #return val if len(val) > 1 else val[0]

        # slight hack for rtlsdr to ignore context object
        return val[0]
"""


if AIO_AVAILABLE:
    try:
        exec('async def test_for_async(): pass')
        exec('def test_unpack_operators(a, *, b): pass')
    except SyntaxError:
        AIO_AVAILABLE = False

if AIO_AVAILABLE:
    exec(_CLASS_TEMPLATE, globals(), locals())

class RtlSdrAio(RtlSdr):
    DEFAULT_READ_SIZE = 128*1024

    def stream(self, num_samples_or_bytes=DEFAULT_READ_SIZE, format='samples', loop=None):
        '''
        Start async streaming from SDR and return an async iterator (Python 3.5+).
        `num_samples_or_bytes` is the number of bytes/samples that will be return each iteration.
        `format` specifies whether raw data ("bytes") or IQ samples ("samples") will be returned.
        `loop` is an asyncio event loop.
        `self.stop()` should be called at some point.
        '''
        if format == 'samples':
            func_start = self.read_samples_async
        elif format == 'bytes':
            func_start = self.read_bytes_async
        else:
            raise ValueError('format "%s" not supported' % format)

        self.async_iter = AsyncCallbackIter(func_start=lambda cb: func_start(cb, num_samples_or_bytes),
                                            func_stop=self.cancel_read_async,
                                            loop=loop)
        self.async_iter.start()

        return self.async_iter

    def stop(self):
        ''' Stop async stream. '''
        self.async_iter.stop()
