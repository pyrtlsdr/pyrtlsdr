PyRtlSdr v0.11 (22/4/2012)
A Python wrapper for librtlsdr (http://sdr.osmocom.org/trac/wiki/rtl-sdr) based
on python-librtlsdr by dbasden (https://github.com/dbasden/python-librtlsdr).

All functions in librtlsdr are accessible via librtlsdr.py. A Pythonic interface
is available in rtlsdr.py (recommended) and includes all major functionality, 
including asynchronous read support. 

No additional dependencies are required, except for the librtlsdr binaries (e.g.
rtlsdr.dll in Windows and librtlsdr.so in Linux), which much be located in the
PyRtlSdr directory, or a system path.

Typical usage:
    > from rtlsdr import RtlSdr
    > sdr = RtlSdr()
    > sdr.rs = 2e6
    > sdr.fc = 70e6
    > print sdr.read_samples(1024)
    ...
    
-- roger_ (http://www.reddit.com/r/RTLSDR/)