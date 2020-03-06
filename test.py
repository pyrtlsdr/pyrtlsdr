#    This file is part of pyrlsdr.
#    Copyright (C) 2013 by Roger <https://github.com/roger-/pyrtlsdr>
#
#    pyrlsdr is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    pyrlsdr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pyrlsdr.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division
from __future__ import print_function

import sys
import argparse

try:
    import numpy as np
    HAVE_NP = True
except ImportError:
    np = None
    HAVE_NP = False

from rtlsdr import *

def get_mean(samples):
    if HAVE_NP:
        r = samples.mean()
    else:
        r = sum(samples)/len(samples)
    return r

def main(**opts):
    rs = opts.get('rs', 2.4e6)
    fc = opts.get('fc', 100e6)
    gain = opts.get('gain', 10)
    num_reads = opts.get('num_reads', 2)
    num_samples = opts.get('num_samples', 256*1024)
    nfft = opts.get('nfft', 1024)
    plot_enabled = opts.get('plot_enabled', False)

    @limit_calls(num_reads)
    def test_callback(samples, rtlsdr_obj):
        print('  in callback, index:', rtlsdr_obj._read_index)
        print('  signal mean:', get_mean(samples))

        all_samples = rtlsdr_obj._all_samples
        if HAVE_NP:
            all_samples[rtlsdr_obj._read_index,:] = samples
        else:
            all_samples.extend(samples)
        rtlsdr_obj._read_index += 1

    sdr = RtlSdr()

    print('Configuring SDR...')
    sdr.rs = rs
    sdr.fc = fc
    sdr.gain = gain
    print('  sample rate: %0.6f MHz' % (sdr.rs/1e6))
    print('  center frequency: %0.6f MHz' % (sdr.fc/1e6))
    print('  gain: %d dB' % sdr.gain)

    print('Reading samples...')
    samples = sdr.read_samples(num_samples)
    print('  signal mean:', get_mean(samples))

    print('Testing callback...')

    if HAVE_NP:
        all_samples = np.zeros((num_reads, num_samples), dtype=np.complex128)
    else:
        all_samples = []

    sdr._all_samples = all_samples
    sdr._read_index = 0
    sdr._num_reads = num_reads

    sdr.read_samples_async(test_callback, num_samples)

    if HAVE_NP:
        all_samples = all_samples.flatten()

    print('Total sample count={}, mean={}'.format(len(all_samples), get_mean(all_samples)))

    if plot_enabled:
        try:
            import pylab as mpl

            print('Testing spectrum plotting...')
            mpl.figure()
            mpl.psd(all_samples, NFFT=nfft, Fc=sdr.fc/1e6, Fs=sdr.rs/1e6)

            mpl.show()
        except:
            # matplotlib not installed/working
            pass

    print('Done\n')
    sdr.close()

class ArgParseFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def _get_default_metavar_for_optional(self, action):
        return action.type.__name__

    def _get_default_metavar_for_positional(self, action):
        return action.type.__name__

def parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    p = argparse.ArgumentParser(formatter_class=ArgParseFormatter)
    p.add_argument(
        '--rs', dest='rs', type=float, default=2.4e6,
        help='Device sample rate',
    )
    p.add_argument(
        '--fc', dest='fc', type=float, default=100e6,
        help='Device center frequency',
    )
    p.add_argument(
        '--gain', dest='gain', type=float, default=10.,
        help='Device gain (dB)',
    )
    p.add_argument(
        '--num-samples', dest='num_samples', type=int, default=256*1024,
        help='Number of samples to read from device per iteration',
    )
    p.add_argument(
        '--num-reads', dest='num_reads', type=int, default=2,
        help='Number of times to read samples (total samples: num_reads * num_samples)',
    )
    p.add_argument(
        '--nfft', dest='nfft', type=int, default=1024,
        help='Number of FFT bins to use for plotting (if matplotlib is available)',
    )
    p.add_argument(
        '--plot', dest='plot_enabled', action='store_true',
        help='Plot the PSD results (if matplotlib is installed)',
    )

    args = p.parse_args(argv)
    opts = vars(args)
    return opts

if __name__ == '__main__':
    opts = parse_args()
    main(**opts)
