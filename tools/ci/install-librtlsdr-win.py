import sys
import shutil
import shlex
import subprocess
import urllib
import tempfile
from pathlib import Path

LIBRTLSDR_TAG = "v0.8.0"
WIN_ZIP_URL = f"https://github.com/librtlsdr/librtlsdr/releases/download/{LIBRTLSDR_TAG}/rtlsdr-bin-w64_static.zip"

def get_archive(dest_path: Path):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        zip_fn = tmpdir / "rtlsdr.zip"
        unpack_dir = tmpdir / "rtlsdr"
        print('Downloading dependencies...')
        response = urllib.urlretrieve(WIN_ZIP_URL, zip_fn)
        
        print(f'Unpacking to {unpack_dir}')
        shutil.unpack_archive(zip_fn, unpack_dir)
        
        for fn in unpack_dir.glob('**/*.dll'):
            print(f'{fn.name} -> {dest_path}')
            shutil.copy2(fn, dest_path)

