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


import os
import re
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

PACKAGE_NAME = 'pyrtlsdr'
VERSION = '0.1.1'

#HERE = os.path.abspath(os.path.dirname(__file__))
#README = open(os.path.join(HERE, 'README.md')).read()

setup(
    name=PACKAGE_NAME,
    version=VERSION,
    author='roger',
    url='https://github.com/roger-/pyrtlsdr',
    download_url='https://github.com/roger-/pyrtlsdr',
    description=('A Python wrapper for librtlsdr (a driver for Realtek RTL2832U based SDR\'s)'),
    #long_description=README,
    classifiers=['Development Status :: 4 - Beta',
                 'Environment :: Console',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: GNU General Public License (GPL)',
                 'Natural Language :: English',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python :: 2.7',
                 'Topic :: Utilities'],
    license='GPLv3',
    keywords='radio librtlsdr rtlsdr sdr',
    packages=['rtlsdr'])