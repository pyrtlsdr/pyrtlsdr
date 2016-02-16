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
import sys
import re
import pre_install
import platform

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup
    find_packages = None

PACKAGE_NAME = 'pyrtlsdr'
VERSION = '0.1.1'

if find_packages is not None:
    if sys.version_info.major <= 3 and sys.version_info.minor < 5:
        PACKAGES = find_packages(exclude=['rtlsdraio.py'])
    else:
        PACKAGES = find_packages()
else:
    PACKAGES = ['rtlsdr']

#HERE = os.path.abspath(os.path.dirname(__file__))
#README = open(os.path.join(HERE, 'README.md')).read()

# PRE INSTALLATION SCRIPT
print('Running pre-installation script...')
try:
    DATA_FILES = pre_install.get_data_files()
except Exception as e:
    DATA_FILES = None
    print('Dependency extraction failed. Please copy required files manually.')

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
    packages=PACKAGES,
    data_files = DATA_FILES,
    )

if platform.system() == 'Windows':
    win_setup(cleanup=True)
