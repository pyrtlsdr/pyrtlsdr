import sys
import shutil
import shlex
import subprocess
from urllib.request import urlopen
import tempfile
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
LIB_DEST = REPO_ROOT / 'rtlsdr'
LIBRTLSDR_TAG = "v0.8.0"
WIN_ZIP_URL = "https://github.com/librtlsdr/librtlsdr/releases/download/{tag}/rtlsdr-bin-w64_static.zip"

def get_archive(dest_path: Path, tag: str = LIBRTLSDR_TAG):
    url = WIN_ZIP_URL.format(tag=tag)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        zip_fn = tmpdir / "rtlsdr.zip"
        unpack_dir = tmpdir / "rtlsdr"
        print('Downloading "{url}"...')
        with urlopen(url) as r:
            zip_fn.write_bytes(r.read())

        print(f'Unpacking to {unpack_dir}')
        shutil.unpack_archive(zip_fn, unpack_dir)

        for fn in unpack_dir.glob('**/*.dll'):
            dest_fn = dest_path / fn.name
            print(f'{fn.name} -> {dest_fn}')
            shutil.copy2(fn, dest_fn)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('-t', '--tag', dest='tag', default=LIBRTLSDR_TAG)
    p.add_argument('out_dir', default=str(LIB_DEST))
    args = p.parse_args()
    args.out_dir = Path(args.out_dir).resolve()

    get_archive(args.out_dir, args.tag)

if __name__ == '__main__':
    main()
