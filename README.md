# Description

pyrtlsdr is a simple Python interface to devices supported by the RTL-SDR project, which turns certain USB DVB-T dongles
employing the Realtek RTL2832U chipset into low-cost, general purpose software-defined radio receivers. It wraps all the
functions in the [librtlsdr library](http://sdr.osmocom.org/trac/wiki/rtl-sdr) (including asynchronous read support),
and also provides a more Pythonic API.

# Usage

All functions in librtlsdr are accessible via librtlsdr.py and a Pythonic interface is available in rtlsdr.py (recommended).
Some documentation can be found in docstrings in the latter file.

## Examples

Simple way to read and print some samples:

```python
from rtlsdr import RtlSdr

sdr = RtlSdr()

# configure device
sdr.sample_rate = 2.048e6
sdr.center_freq = 70e6
sdr.gain = 'auto'

print sdr.read_samples(512)
```

Plotting the PSD with matplotlib:

```python
from pylab import *
from rtlsdr import *

sdr = RtlSdr()

# configure device
sdr.sample_rate = 2.4e6
sdr.center_freq = 95e6
sdr.gain = 4

samples = sdr.read_samples(256*1024)

# use matplotlib to estimate and plot the PSD
psd(samples, NFFT=1024, Fs=sdr.sample_rate/1e6, Fc=sdr.center_freq/1e6)
xlabel('Frequency (MHz)')
ylabel('Relative power (dB)')

show()
```

Resulting plot [here](http://i.imgur.com/hFhg8.png).

See the files 'demo_waterfall.py' and 'test.py' for more examples.

# Dependencies

* Windows/Linux/OSX
* Python 2.7.x
* librtlsdr (builds dated after 5/5/12)
* **Optional**: distribute (a fork of the Setuptools project) for using setup script
* **Optional**: NumPy (wraps samples in a more convenient form)

matplotlib is also useful for plotting data. The librtlsdr binaries (rtlsdr.dll in Windows and librtlsdr.so in Linux)
should be in the pyrtlsdr directory, or a system path. Note that these binaries may have additional dependencies.

# Credit

Credit to dbasden for his earlier wrapper [python-librtlsdr](https://github.com/dbasden/python-librtlsdr).

-- Roger
