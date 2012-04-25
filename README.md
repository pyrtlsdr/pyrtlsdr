# Description

pyrtlsdr is a simple Python interface to devices supported by the RTL-SDR project, which turns certain USB DVB-T dongles 
employing the Realtek RTL2832U chipset into low-cost, general purpose software-defined radio receivers. It wraps all the 
functions in the [librtlsdr library](http://sdr.osmocom.org/trac/wiki/rtl-sdr) (including asynchronous read support), 
and also provides a more Pythonic API.

# Dependencies

* Windows/Linux/OSX
* Python 2.7.x
* librtlsdr (support for changed introduced on 4/24 will be added soon)
* **Optional**: NumPy (wraps data in a more convenient form)

matplotlib is also useful for plotting data. The librtlsdr binaries (rtlsdr.dll in Windows and librtlsdr.so in Linux) 
should be in the pyrtlsdr directory, or a system path.

# Usage

All functions in librtlsdr are accessible via librtlsdr.py. A Pythonic interface is available in rtlsdr.py (recommended).

Typical usage:

```python
from rtlsdr import RtlSdr

sdr = RtlSdr()
sdr.rs = 2e6
sdr.fc = 70e6
print sdr.read_samples(1024)
```

See the files 'test.py' for more examples.

# Credit

Credit to dbasden for his earlier wrapper [python-librtlsdr](https://github.com/dbasden/python-librtlsdr).

-- Roger
