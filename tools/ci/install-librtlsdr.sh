#!/bin/sh
# Linux script to build and install librtlsdr
# Based on steps found at sdr.osmocom.org/trac/wiki/rtl-sdr

DEFAULT_RELEASE="master"
RELEASE=${1:-$DEFAULT_RELEASE}
TAR_FILE="$RELEASE.tar.gz"
PKG_URL="https://github.com/librtlsdr/librtlsdr/archive/$TAR_FILE"

if [ "$CI" = "true" ]; then
  set -ex
fi

mkdir -p build
cd build
if [ -d "librtlsdr-$RELEASE" ]; then
  echo "Removing old build files"
  rm -Rf "librtlsdr-$RELEASE"
fi
echo "Building librtlsdr v$RELEASE from $PKG_URL"
wget $PKG_URL
tar xvzf $TAR_FILE
cd "librtlsdr-$RELEASE"
mkdir build
cd build
if [ "$CI" = "true" ]; then
  cmake -DCMAKE_INSTALL_PREFIX=$HOME/.local -DLIB_INSTALL_DIR=$HOME/.local/ ../
  make
  make install
else
  cmake ../
  make
  sudo make install
fi
