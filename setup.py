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
try:
    from setuptools import setup
    from setuptools.command.install_lib import install_lib as _install_lib
except ImportError:
    from distutils.core import setup
    from distutils.command.install_lib import install_lib as _install_lib
try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:
    bdist_wheel = None

PACKAGE_NAME = 'pyrtlsdr'
VERSION = '0.2.2'

ASYNC_AVAILABLE = sys.version_info.major >= 3
if sys.version_info.major == 3:
    ASYNC_AVAILABLE = sys.version_info.minor >= 5

class install_lib(_install_lib):
    def byte_compile(self, files):
        if not ASYNC_AVAILABLE:
            files = [f for f in files if 'rtlsdraio.py' not in f]
        _install_lib.byte_compile(self, files)

CMDCLASS = {'install_lib':install_lib}

if bdist_wheel is not None:

    # We want to build a wheel for py3 (python < 3.5) and a wheel for py35
    # This could be done with command line arguments, but they can't easily be
    # added to the deploy config in travis-ci.

    class bdist_wheel_(bdist_wheel):
        def initialize_options(self):
            bdist_wheel.initialize_options(self)
            v = sys.version_info
            if ASYNC_AVAILABLE and v[0] == 3:
                self.python_tag = 'py{0}{1}'.format(v[0], v[1])
    CMDCLASS['bdist_wheel'] = bdist_wheel_

#HERE = os.path.abspath(os.path.dirname(__file__))
#README = open(os.path.join(HERE, 'README.md')).read()

setup(
    name=PACKAGE_NAME,
    version=VERSION,
    author='roger',
    url='https://github.com/roger-/pyrtlsdr',
    download_url='https://github.com/roger-/pyrtlsdr',
    description=('A Python wrapper for librtlsdr (a driver for Realtek RTL2832U based SDR\'s)'),
    long_description_markdown_filename='README.md',
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
    setup_requires=['setuptools-markdown'],
    cmdclass=CMDCLASS,
    packages=['rtlsdr'])
