import sys
import pytest
import itertools

def test_pkg_version():
    import subprocess
    import rtlsdr

    setup_version = subprocess.check_output(['python', 'setup.py', '-V'])
    if isinstance(setup_version, bytes):
        setup_version = setup_version.decode('UTF-8')
    setup_version = setup_version.splitlines()[0]

    assert rtlsdr.__version__ == setup_version

def test(sdr_cls, use_numpy):
    from utils import generic_test
    sdr = sdr_cls()
    generic_test(sdr, use_numpy=use_numpy)
    sdr.close()

@pytest.mark.skipif(sys.version_info < (3, 5), reason="requires python3.5 or higher")
def test_example_script(capsys, use_numpy):
    from pathlib import Path
    import rtlsdr

    SAMPLE_RATES = [1.024e6, 2.048e6]
    CENTER_FREQS = [100e6, 200e6, 300e6]
    GAINS = [10, 20, 30]
    NUM_SAMPLES = 4096
    NUM_READS = 8

    here = Path(__file__).resolve().parent
    script_fn = here.parent / 'test.py'
    assert script_fn.exists()

    mod_dict = {'__builtins__':__builtins__, 'rtlsdr':rtlsdr}
    mod = compile(script_fn.read_text(), str(script_fn), mode='exec')
    exec(mod, mod_dict)

    mod_dict['HAVE_NP'] = use_numpy
    mod_dict['HAVE_NP'] = use_numpy
    parse_args = mod_dict['parse_args']
    main = mod_dict['main']


    def iter_output_sections(outstr):
        cur_section = None
        content = []
        for line in outstr.splitlines():
            content.append(line)
            if line.startswith('Configuring SDR'):
                assert cur_section is None
                cur_section = 'config'
            elif line.startswith('Reading samples'):
                assert cur_section == 'config'
                yield cur_section, content
                content = []
                cur_section = 'read_sync'
            elif line.startswith('Testing callback'):
                assert cur_section == 'read_sync'
                yield cur_section, content
                content = []
                cur_section = 'read_async'
            elif line.startswith('Total sample count'):
                assert cur_section == 'read_async'
                yield cur_section, content
                content = []
                cur_section = 'totals'
            elif line.startswith('Done'):
                break

    for rs, fc, gain in itertools.product(SAMPLE_RATES, CENTER_FREQS, GAINS):
        argv = [
            '--rs', '{:.0f}'.format(rs),
            '--fc', '{:.0f}'.format(fc),
            '--gain', str(gain),
            '--num-samples', str(NUM_SAMPLES),
            '--num-reads', str(NUM_READS),
        ]
        opts = parse_args(argv)
        main(**opts)
        captured = capsys.readouterr()
        for section, content in iter_output_sections(captured.out):
            if section == 'config':
                for line in section:
                    if 'sample rate' in line:
                        val = float(line.split(':')[1])
                        assert val == rs
                    elif 'center frequency' in line:
                        val = float(line.split(':')[1])
                        assert val == fc
                    elif 'gain' in line:
                        val = float(line.split(':').rstip('dB'))
                        assert val == gain
            elif section == 'totals':
                line = content[0]
                total_count = int(line.split('sample count=')[1].split(',')[0])
                assert total_count == NUM_SAMPLES * NUM_READS


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

    def fake_callback(*args):
        pass

    TEST_METHODS = [
        ('set_center_freq', [100e6]),
        ('get_center_freq', []),
        ('set_freq_correction', [0]),
        ('get_freq_correction', []),
        ('set_sample_rate', [1.024e6]),
        ('get_sample_rate', []),
        ('set_bandwidth', [1.024e6]),
        ('set_gain', [10]),
        ('set_manual_gain_enabled', [True]),
        ('set_agc_mode', [True]),
        ('set_direct_sampling', ['q']),
        ('get_tuner_type', []),
        ('read_bytes', []),
        ('read_samples', []),
        ('read_bytes_async', [fake_callback]),
        ('read_samples_async', [fake_callback]),
        ('cancel_read_async', []),
    ]

    from rtlsdr.rtlsdr import RtlSdr, LibUSBError

    for errno in LibUSBError._errno_map.keys():
        err_id, err_msg = LibUSBError._errno_map[errno]

        # Ensure no errors are thrown during initialization
        monkeypatch.setattr(testlibrtlsdr, 'ERROR_CODE', 0)

        sdr = RtlSdr()

        # Now tell our mocked librtlsdr to always throw errors
        monkeypatch.setattr(testlibrtlsdr, 'ERROR_CODE', errno)

        for meth_name, meth_args in TEST_METHODS:
            m = getattr(sdr, meth_name)
            print(m)
            with pytest.raises(LibUSBError) as exc:
                if len(meth_args):
                    m(*meth_args)
                else:
                    m()
            assert exc.value.errno == errno
            assert err_id in str(exc.value)
            assert err_msg in str(exc.value)
