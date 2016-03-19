
def test(sdr_cls):
    from utils import generic_test
    sdr = sdr_cls()
    generic_test(sdr)
    sdr.close()
