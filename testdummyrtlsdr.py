from rtlsdr.testutils import DummyRtlSdr
from test import test


if __name__ == '__main__':
    sdr = DummyRtlSdr()
    test(sdr)
