#!/usr/bin/env python3
"""Build the Akasha OS ambient photo pack.

Called by scripts/apply.sh on the build host. It downloads the curated set of
Wikimedia Commons landscape photos (kodi/scripts/ambient-download-photos.py)
and downscales them with ffmpeg so the Raspberry Pi 4 does not have to decode
full-resolution "Featured pictures" (some originals are 40+ megapixels /
30+ MB) just to display a 1920x1080 screensaver slideshow.

The output folder is meant to be bundled into the deploy tarball and copied to
/storage/ambient/photos by scripts/install.sh. Docker with the
jrottenberg/ffmpeg image is required for the resize step when ffmpeg is not
installed locally (same fallback as scripts/prepare-ambient-videos.py).
"""
import argparse
import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DOWNLOAD_SCRIPT = os.path.join(REPO_ROOT, 'kodi', 'scripts', 'ambient-download-photos.py')
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, 'kodi', 'media', 'ambient-photos')
DEFAULT_CACHE_DIR = os.path.join(REPO_ROOT, '.cache', 'ambient-photos-raw')
MANIFEST_NAME = '.akasha-ambient-photos'


def _ensure_ffmpeg():
    """Return the ffmpeg invocation. Prefer local binary, fallback to Docker."""
    if shutil.which('ffmpeg'):
        return ['ffmpeg']
    if shutil.which('docker'):
        return [
            'docker', 'run', '--rm',
            '-v', '{}:{}'.format(REPO_ROOT, REPO_ROOT),
            '-w', REPO_ROOT,
            'jrottenberg/ffmpeg:4.4-ubuntu',
        ]
    raise RuntimeError('ffmpeg not found and Docker is not available')


def _resize(src, dest, ffmpeg_cmd, max_dimension=1920):
    """Downscale a photo to fit within max_dimension while keeping aspect ratio."""
    abs_src = os.path.abspath(src)
    abs_dest = os.path.abspath(dest)
    tmp_dest = abs_dest + '.tmp.jpg'

    cmd = list(ffmpeg_cmd)
    cmd += [
        '-y', '-i', abs_src,
        # Only downscale (never upscale) landscape photos to fit 1920x1080.
        '-vf', "scale='min({0},iw)':'min(1080,ih)':force_original_aspect_ratio=decrease".format(max_dimension),
        '-q:v', '3',
        tmp_dest,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.replace(tmp_dest, abs_dest)


def _read_manifest(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def prepare_photos(out_dir=DEFAULT_OUT_DIR, cache_dir=DEFAULT_CACHE_DIR, timeout=180):
    """Download and downscale the default ambient photo pack."""
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    result = subprocess.run(
        [sys.executable, DOWNLOAD_SCRIPT, cache_dir, '--timeout', str(timeout)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    print(result.stdout, end='')
    if result.returncode != 0:
        print('prepare-ambient-photos: Commons download failed; will use cached files if any.',
              file=sys.stderr)

    manifest_path = os.path.join(cache_dir, MANIFEST_NAME)
    manifest = _read_manifest(manifest_path)

    if not manifest:
        manifest = sorted(f for f in os.listdir(cache_dir)
                           if f.lower().endswith(('.jpg', '.jpeg', '.png')))

    if not manifest:
        print('prepare-ambient-photos: no source photos available', file=sys.stderr)
        return 0

    ffmpeg_cmd = _ensure_ffmpeg()

    target_names = set(manifest)
    for name in os.listdir(out_dir):
        if name != MANIFEST_NAME and name not in target_names:
            print('Removing stale ambient photo: {}'.format(name))
            try:
                os.remove(os.path.join(out_dir, name))
            except OSError:
                pass

    produced = 0
    for name in manifest:
        src_path = os.path.join(cache_dir, name)
        if not os.path.exists(src_path):
            print('prepare-ambient-photos: source missing for {}'.format(name), file=sys.stderr)
            continue
        dest_path = os.path.join(out_dir, name)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            print('Already prepared: {}'.format(name))
            produced += 1
            continue
        try:
            print('Resizing {} -> {}'.format(src_path, dest_path))
            _resize(src_path, dest_path, ffmpeg_cmd)
            print('Prepared: {}'.format(dest_path))
            produced += 1
        except subprocess.CalledProcessError as e:
            print('prepare-ambient-photos: failed to resize {}: {}'.format(src_path, e),
                  file=sys.stderr)
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except OSError:
                    pass

    if produced:
        shutil.copyfile(manifest_path, os.path.join(out_dir, MANIFEST_NAME))

    return produced


def main():
    parser = argparse.ArgumentParser(
        description='Build the Akasha OS downscaled ambient photo pack.',
    )
    parser.add_argument('--out', default=DEFAULT_OUT_DIR,
                        help='Output directory for resized photos.')
    parser.add_argument('--cache', default=DEFAULT_CACHE_DIR,
                        help='Cache directory for raw Commons downloads.')
    parser.add_argument('-t', '--timeout', type=int, default=180,
                        help='HTTP timeout in seconds (default: 180).')
    args = parser.parse_args()

    produced = prepare_photos(out_dir=args.out, cache_dir=args.cache, timeout=args.timeout)
    if produced > 0:
        print('Prepared {} ambient photo(s) in {}'.format(produced, args.out))
        return 0
    print('No ambient photos prepared.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
