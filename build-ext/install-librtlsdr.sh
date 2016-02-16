#!/bin/sh
# Linux script to build and install librtlsdr
# Based on steps found at sdr.osmocom.org/trac/wiki/rtl-sdr

DEFAULT_RELEASE="0.5.3"
RELEASE=${1:-$DEFAULT_RELEASE}
TAR_FILE="v$RELEASE.tar.gz"
PKG_URL="https://github.com/steve-m/librtlsdr/archive/$TAR_FILE"

if [ "$TRAVIS" = "true"]; then
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
cmake ../
make
sudo make install
sudo ldconfig
