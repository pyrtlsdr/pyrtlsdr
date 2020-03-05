import pytest

def test_pkg_version():
    import subprocess
    import rtlsdr

    setup_version = subprocess.check_output(['python', 'setup.py', '-V'])
    if isinstance(setup_version, bytes):
        setup_version = setup_version.decode('UTF-8')
    setup_version = setup_version.strip('\n')

    assert rtlsdr.__version__ == setup_version

def test(sdr_cls, use_numpy):
    from utils import generic_test
    sdr = sdr_cls()
    generic_test(sdr, use_numpy=use_numpy)
    sdr.close()

def test_serial_addressing(sdr_cls, use_numpy):
    for i, serial in enumerate(sdr_cls.get_device_serial_addresses()):
        assert sdr_cls.get_device_index_by_serial(serial) == i
        sdr = sdr_cls(serial_number=serial)
        sdr.close()

def test_error_codes(monkeypatch):
    import testlibrtlsdr
    for attr in ['p_rtlsdr_dev', 'librtlsdr', 'rtlsdr_read_async_cb_t']:
        lib_attr = '.'.join(['rtlsdr', 'rtlsdr', attr])
        override = getattr(testlibrtlsdr, attr)
        monkeypatch.setattr(lib_attr, override)

    from rtlsdr.rtlsdr import RtlSdr, LibUSBError

    for errno in LibUSBError._errno_map.keys():
        err_id, err_msg = LibUSBError._errno_map[errno]

        monkeypatch.setattr(testlibrtlsdr, 'ERROR_CODE', errno)

        with pytest.raises(LibUSBError) as exc:
            sdr = RtlSdr()

        assert exc.value.errno == errno
        assert err_id in str(exc.value)
        assert err_msg in str(exc.value)
