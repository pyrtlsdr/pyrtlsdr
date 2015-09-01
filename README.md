# Description

pyrtlsdr is a simple Python interface to devices supported by the RTL-SDR project, which turns certain USB DVB-T dongles
employing the Realtek RTL2832U chipset into low-cost, general purpose software-defined radio receivers. It wraps many of the
functions in the [librtlsdr library](http://sdr.osmocom.org/trac/wiki/rtl-sdr) (including asynchronous read support),
and also provides a more Pythonic API.

# Usage

pyrtlsdr can be installed by downloading the source files and running `python setup.py install`, or using [pip](http://www.pip-installer.org/en/latest/) and
`pip install pyrtlsdr`.

All functions in librtlsdr are accessible via librtlsdr.py and a Pythonic interface is available in rtlsdr.py (recommended).
Some documentation can be found in docstrings in the latter file.

## Examples

Simple way to read and print some samples:

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
* Python 2.7.x/3.3+
* librtlsdr (builds dated after 5/5/12)
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
  * **Windows**: Make sure all the DLL files are in your system path, or the same folder
as this README file. Also make sure you have all of *their* dependencies (e.g. the Visual Studio runtime files). If rtl_sdr.exe
works, then you should be okay. Also note that you can't mix the 64 bit version of Python with 32 bit builds of librtlsdr, and vice versa.
  * **Linux**: Make sure your LD_LIBRARY_PATH environment variable contains the directory where the librtlsdr.so.0 library is located. You can do this in a shell with (for example): `export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib`. See [here](https://github.com/roger-/pyrtlsdr/issues/7) for more details.

# License

All of the code contained here is licensed by the GNU General Public License v3.

# Credit

Credit to dbasden for his earlier wrapper [python-librtlsdr](https://github.com/dbasden/python-librtlsdr) and all the
contributers on GitHub.

Copyright (C) 2013 by Roger <https://github.com/roger->
