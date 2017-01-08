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

def test_lib_error_codes(librtlsdr_error_checking):
    RtlSdr, librtlsdr = librtlsdr_error_checking

    librtlsdr.fail_tests_on_open = True
    with pytest.raises(IOError):
        sdr = RtlSdr()

    librtlsdr.fail_tests_on_open = False
    librtlsdr.fail_tests = True

    with pytest.raises(IOError, message='Error code -1 when setting test mode'):
        sdr = RtlSdr(test_mode_enabled=True)
    with pytest.raises(IOError, message='Error code -1 when resetting buffer (device index = 0)'):
        sdr = RtlSdr()

    librtlsdr.fail_tests = False
    sdr = RtlSdr()
    librtlsdr.fail_tests = True

    fc = 90e6
    with pytest.raises(IOError, message='Error code -1 when setting center freq. to %d Hz' % (fc)):
        sdr.fc = fc
    with pytest.raises(IOError, message='Error code 0 when getting center freq.'):
        sdr.get_center_freq()
    with pytest.raises(IOError, message='Error code -1 when setting freq. offset to 10 ppm'):
        sdr.set_freq_correction(10)

    ## TODO: There is no return value documented as an 'error'
    ## (which would make sense if you had a negative offset in PPM)
    # with pytest.raises(IOError, message='Error code ? when getting freq. offset in ppm.'):
    #     sdr.get_freq_correction()

    rs = 2e6
    with pytest.raises(IOError, message='Error code -1 when setting sample rate to %d Hz' % (rs)):
        sdr.rs = rs

    with pytest.raises(IOError, message='Error code 0 when getting sample rate'):
        sdr.get_sample_rate()

    with pytest.raises(IOError, message='Error when getting gains'):
        gains = sdr.get_gains()
