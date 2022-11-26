# pyrtlsdr
A Python wrapper for librtlsdr (a driver for Realtek RTL2832U based SDR's)

[![PyPI](https://img.shields.io/pypi/v/pyrtlsdr)](https://pypi.org/project/pyrtlsdr) ![GitHub Workflow Status](https://img.shields.io/github/workflow/status/pyrtlsdr/pyrtlsdr/Python%20package) ![PyPI - Downloads](https://img.shields.io/pypi/dm/pyrtlsdr) [![Coveralls](https://img.shields.io/coveralls/github/pyrtlsdr/pyrtlsdr)](https://coveralls.io/github/pyrtlsdr/pyrtlsdr)

# Description

pyrtlsdr is a simple Python interface to devices supported by the RTL-SDR project, which turns certain USB DVB-T dongles
employing the Realtek RTL2832U chipset into low-cost, general purpose software-defined radio receivers. It wraps many of the
functions in the [librtlsdr library](https://github.com/librtlsdr/librtlsdr) including asynchronous read support
and also provides a more Pythonic API.

# Links

* Documentation:
  * https://pyrtlsdr.readthedocs.io/
* Releases:
  * https://pypi.org/project/pyrtlsdr/
* Source code and project home:
  * https://github.com/pyrtlsdr/pyrtlsdr
* Releases for `librtlsdr`:
  * https://github.com/librtlsdr/librtlsdr/releases

# Usage

pyrtlsdr can be installed by downloading the source files and running `python setup.py install`, or using [pip](https://pip.pypa.io/en/stable/) and
`pip install pyrtlsdr`.

All functions in librtlsdr are accessible via librtlsdr.py and a Pythonic interface is available in rtlsdr.py (recommended).
Some documentation can be found in docstrings in the latter file.

## Examples

### Simple way to read and print some samples:

```python
from rtlsdr import RtlSdr

sdr = RtlSdr()

# configure device
sdr.sample_rate = 2.048e6  # Hz
sdr.center_freq = 70e6     # Hz
sdr.freq_correction = 60   # PPM
sdr.gain = 'auto'

print(sdr.read_samples(512))
```

### Plotting the PSD with matplotlib:

```python
from pylab import *
from rtlsdr import *

sdr = RtlSdr()

# configure device
sdr.sample_rate = 2.4e6
sdr.center_freq = 95e6
sdr.gain = 4

samples = sdr.read_samples(256*1024)
sdr.close()

# use matplotlib to estimate and plot the PSD
psd(samples, NFFT=1024, Fs=sdr.sample_rate/1e6, Fc=sdr.center_freq/1e6)
xlabel('Frequency (MHz)')
ylabel('Relative power (dB)')

show()
```

### Resulting Plot:
![](https://i.imgur.com/hFhg8.png "Resulting Plot")

See the files 'demo_waterfall.py' and 'test.py' for more examples.

## Handling multiple devices:
*(added in v2.5.6)*
```python
from rtlsdr import RtlSdr

# Get a list of detected device serial numbers (str)
serial_numbers = RtlSdr.get_device_serial_addresses()

# Find the device index for a given serial number
device_index = RtlSdr.get_device_index_by_serial('00000001')

sdr = RtlSdr(device_index)


# Or pass the serial number directly:
sdr = RtlSdr(serial_number='00000001')
```

### Note
Most devices by default have the same serial number: '0000001'. This can be set
to a custom value by using the [rtl_eeprom][rtl_eeprom] utility packaged with `librtlsdr`.

[rtl_eeprom]: https://manpages.ubuntu.com/manpages/trusty/man1/rtl_eeprom.1.html

# Experimental features

Two new submodules are available for testing: **rtlsdraio**, which adds native Python 3 asynchronous support (asyncio module), and **rtlsdrtcp** which adds a TCP server/client for accessing a device over the network. See the respective modules in the rtlsdr folder for more details and feel free to test and report any bugs!

## rtlsdraio
Note that the rtlsdraio module is automatically imported and adds `stream()` and `stop()` methods to the normal `RtlSdr` class. It also requires the new `async`/`await` syntax introduced in Python 3.5+.

The syntax is basically:

```python
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
```

## rtlsdrtcp
The `RtlSdrTcpServer` class is meant to be connected physically to an SDR dongle and communicate with an instance of `RtlSdrTcpClient`. The client is intended to function as closely as possible to the base RtlSdr class (as if it had a physical dongle attached to it).

Both of these classes have the same arguments as the base `RtlSdr` class with the addition of `hostname` and `port`:
```python
server = RtlSdrTcpServer(hostname='192.168.1.100', port=12345)
server.run_forever()
# Will listen for clients until Ctrl-C is pressed
```
```python
# On another machine (typically)
client = RtlSdrTcpClient(hostname='192.168.1.100', port=12345)
client.center_freq = 2e6
data = client.read_samples()
```

## TCP Client Mode
On platforms where the `librtlsdr` library cannot be installed/compiled, it is possible to import the `RtlSdrTcpClient` only by setting the environment variable `"RTLSDR_CLIENT_MODE"` to `"true"`. If this is set, no other modules will be available.

*Feature added in v0.2.4*


# Dependencies

* Windows/Linux/OSX
* Python 2.7.x/3.3+
* [librtlsdr](https://github.com/librtlsdr/librtlsdr/releases)
* **Optional**: NumPy (wraps samples in a more convenient form)

matplotlib is also useful for plotting data. The librtlsdr binaries (rtlsdr.dll in Windows and librtlsdr.so in Linux)
should be in the pyrtlsdr directory, or a system path. Note that these binaries may have additional dependencies.

# Todo

There are a few remaining functions in librtlsdr that haven't been wrapped yet. It's a simple process if there's an additional
function you need to add support for, and please send a pull request if you'd like to share your changes.

# Troubleshooting

* Some operating systems (Linux, OS X) seem to result in libusb buffer issues when performing small reads. Try reading 1024
(or higher powers of two) samples at a time if you have problems.

* If you're having librtlsdr import errors:
  * **Windows**: Make sure all the librtlsdr DLL files (librtlsdr.dll, libusb-1.0.dll) are in your system path, or the same folder
as this README file. Also make sure you have all of *their* dependencies (e.g. libgcc_s_dw2-1.dll or possibly the Visual Studio runtime files). If rtl_sdr.exe
works, then you should be okay. Also note that you can't mix the 64 bit version of Python with 32 bit builds of librtlsdr, and vice versa.
  * **Linux**: Make sure your LD_LIBRARY_PATH environment variable contains the directory where the librtlsdr.so.0 library is located. You can do this in a shell with (for example): `export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib`. See [this issue](https://github.com/roger-/pyrtlsdr/issues/7) for more details.

# License

All of the code contained here is licensed by the GNU General Public License v3.

# Credit

Credit to dbasden for his earlier wrapper [python-librtlsdr](https://github.com/dbasden/python-librtlsdr) and all the
contributors on GitHub.

Copyright (C) 2013 by Roger <https://github.com/pyrtlsdr/pyrtlsdr>
