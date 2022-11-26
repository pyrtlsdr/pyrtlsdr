"""
This module adds :mod:`asyncio` support for reading samples from the device.

The main functionality can be found in the :meth:`~rtlsdr.rtlsdraio.RtlSdrAio.stream`
method of :class:`rtlsdr.rtlsdraio.RtlSdrAio`.

Example:
    .. code-block:: python

       import asyncio
       from rtlsdr import RtlSdr

       async def streaming():
           sdr = RtlSdr()

           async for samples in sdr.stream():
               # do something with samples
               # ...

           # to stop streaming:
           await sdr.stop()

           # done
           sdr.close()

       loop = asyncio.get_event_loop()
       loop.run_until_complete(streaming())

"""

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
    '''Convert a callback-based legacy async function into one supporting asyncio
    and Python 3.5+

    The queued data can be iterated using ``async for``

    Arguments:
        func_start: A callable which should take a single callback that will be
            passed data. Will be run in a separate thread in case it blocks.
        func_stop (optional): A callable to stop ``func_start`` from calling the
            callback. Will be run in a separate thread in case it blocks.
        queue_size (:obj:`int`, optional): The maximum amount of data
            that will be buffered.
        loop (optional): The ``asyncio.event_loop`` to use. If not supplied,
            :func:`asyncio.get_event_loop` will be used.

    '''

    def __init__(self, func_start, func_stop=None, queue_size=20, *, loop=None):
        self.queue = asyncio.Queue(queue_size)
        self.loop = loop if loop else asyncio.get_event_loop()
        self.func_stop = func_stop
        self.func_start = func_start

        self.running = False

    async def add_to_queue(self, *args):
        '''Add items to the queue

        Arguments:
            *args: Arguments to be added

        This method is a :obj:`~asyncio.coroutine`
        '''
        try:
            self.queue.put_nowait(args)
        except asyncio.QueueFull:
            log.info('extra callback data lost')

    def _callback(self, *args):
        if not self.running:
            return
        asyncio.run_coroutine_threadsafe(self.add_to_queue(*args), self.loop)

    async def start(self):
        '''Start the execution

        The callback given by ``func_start`` will be called by
        :meth:`asyncio.AbstractEventLoop.run_in_executor` and will continue
        until :meth:`stop` is called.

        This method is a :obj:`~asyncio.coroutine`
        '''

        assert(not self.running)

        # start legacy async function
        future = self.loop.run_in_executor(None, self.func_start, self._callback)
        asyncio.ensure_future(future, loop=self.loop)
        self.executor_task = future
        self.running = True

    async def stop(self):
        '''Stop the running executor task

        If ``func_stop`` was supplied, it will be called after the queue has
        been exhausted.

        This method is a :obj:`~asyncio.coroutine`
        '''

        assert(self.running)

        self.running = False

        # send a signal to stop
        iter_stopped = False
        while not iter_stopped:
            try:
                self.queue.put_nowait((StopAsyncIteration(),))
                iter_stopped = True
            except asyncio.QueueFull:
                try:
                    self.queue.task_done()
                except ValueError:
                    pass
        if self.func_stop:
            # stop legacy async function
            await self.loop.run_in_executor(None, self.func_stop)
        await self.executor_task

    def __aiter__(self):
        return self

    async def __anext__(self):
        val = await self.queue.get()
        self.queue.task_done()

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
        """Start async streaming from SDR and return an async iterator (Python 3.5+).

        The :meth:`read_samples_async` method is called in an  :class:`~concurrent.futures.Excecutor`
        instance using :meth:`asyncio.AbstractEventLoop.run_in_executor`.

        The returned asynchronous iterable can then used to retrieve sample
        data using ``async for`` syntax.

        Calling the :meth:`~rtlsdr.rtlsdraio.RtlSdrAio.stop` method will stop
        the ``read_samples_async`` session and close the ``Excecutor`` task.

        Arguments:
            num_samples_or_bytes (int): The number of bytes/samples that will be
                returned each iteration
            format (:obj:`str`, optional): Specifies whether raw data ("bytes")
                or IQ samples ("samples") will be returned
            loop (optional): An asyncio event loop

        Returns:
            An ``asynchronous iterator`` to yield sample data
        """
        if format == 'samples':
            func_start = self.read_samples_async
        elif format == 'bytes':
            func_start = self.read_bytes_async
        else:
            raise ValueError('format "%s" not supported' % format)

        self.async_iter = AsyncCallbackIter(func_start=lambda cb: func_start(cb, num_samples_or_bytes),
                                            func_stop=self.cancel_read_async,
                                            loop=loop)
        asyncio.ensure_future(self.async_iter.start(), loop=loop)

        return self.async_iter

    def stop(self):
        """Stop async stream

        Stops the ``read_samples_async`` and ``Excecutor`` task created by
        :meth:`stream`.
        """
        return asyncio.ensure_future(self.async_iter.stop(), loop=self.async_iter.loop)
