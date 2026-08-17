#!/usr/bin/env python3
"""Build the Akasha OS ambient video pack.

Called by scripts/apply.sh on the build host. It downloads a curated set of
freely licensed landscape videos from Wikimedia Commons and transcodes them to
H.264/AAC .mp4 so LibreELEC/Kodi on the Raspberry Pi 4 can decode them reliably.

The output folder is meant to be bundled into the deploy tarball and copied to
/storage/ambient/photos by scripts/install.sh. Docker with the jrottenberg/ffmpeg
image is required for the transcoding step when ffmpeg is not installed locally.
"""
import argparse
import os
import shutil
import subprocess
import sys
import unicodedata

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
COMMONS_SCRIPT = os.path.join(REPO_ROOT, 'kodi', 'scripts', 'ambient-download-videos.py')
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, 'kodi', 'media', 'ambient')
DEFAULT_CACHE_DIR = os.path.join(REPO_ROOT, '.cache', 'ambient-raw')


def _asciify(name):
    """Replace accented/non-ASCII characters with ASCII equivalents."""
    nfkd = unicodedata.normalize('NFKD', name)
    return ''.join(c for c in nfkd if ord(c) < 128)


def _safe_mp4_name(filename):
    """Derive a clean .mp4 filename from a source video filename."""
    base, _ = os.path.splitext(filename)
    base = _asciify(base)
    base = base.replace(' ', '_')
    for ch in ['/', '\\', '<', '>', ':', '"', '|', '?', '*', ',']:
        base = base.replace(ch, '_')
    while '__' in base:
        base = base.replace('__', '_')
    return base.strip('_') + '.mp4'


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


def _transcode(src, dest, ffmpeg_cmd):
    """Transcode a source video to H.264/AAC MP4."""
    abs_src = os.path.abspath(src)
    abs_dest = os.path.abspath(dest)
    # Use a .mp4 extension so ffmpeg infers the container format, then atomically
    # rename to the final file.
    tmp_dest = abs_dest + '.tmp.mp4'

    # The Docker invocation uses the image's ffmpeg entrypoint.
    cmd = list(ffmpeg_cmd)

    cmd += [
        '-y', '-i', abs_src,
        '-c:v', 'libx264',
        '-profile:v', 'high',
        '-level:v', '4.0',
        '-preset', 'medium',
        '-crf', '28',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-c:a', 'aac',
        '-b:a', '96k',
        '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
        tmp_dest,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    os.replace(tmp_dest, abs_dest)


def _read_manifest(manifest_path):
    if not os.path.exists(manifest_path):
        return []
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def prepare_videos(out_dir=DEFAULT_OUT_DIR, cache_dir=DEFAULT_CACHE_DIR, timeout=180):
    """Download and transcode the default ambient video pack."""
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    # Download the raw Commons videos into the cache directory.
    result = subprocess.run(
        [sys.executable, COMMONS_SCRIPT, cache_dir, '--timeout', str(timeout)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    print(result.stdout, end='')
    if result.returncode != 0:
        print('prepare-ambient-videos: Commons download failed; will use cached files if any.',
              file=sys.stderr)

    manifest_path = os.path.join(cache_dir, '.akasha-ambient-videos')
    manifest = _read_manifest(manifest_path)

    if not manifest:
        # Fall back to listing the cache directory.
        manifest = sorted(f for f in os.listdir(cache_dir)
                          if f.lower().endswith(('.webm', '.ogv', '.mp4')))

    if not manifest:
        print('prepare-ambient-videos: no source videos available', file=sys.stderr)
        return 0

    ffmpeg_cmd = _ensure_ffmpeg()

    # Build expected output set and remove stale MP4s.
    target_outputs = {}
    for name in manifest:
        target_outputs[_safe_mp4_name(name)] = os.path.join(cache_dir, name)

    for name in os.listdir(out_dir):
        if name.endswith('.mp4') and name not in target_outputs:
            print('Removing stale ambient video: {}'.format(name))
            try:
                os.remove(os.path.join(out_dir, name))
            except OSError:
                pass

    produced = 0
    for mp4_name, src_path in target_outputs.items():
        if not os.path.exists(src_path):
            print('prepare-ambient-videos: source missing for {}'.format(mp4_name),
                  file=sys.stderr)
            continue
        dest_path = os.path.join(out_dir, mp4_name)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            src_size = os.path.getsize(src_path)
            dest_size = os.path.getsize(dest_path)
            # Heuristic: a valid H.264 MP4 is usually larger than 20% of a WebM.
            if dest_size > src_size * 0.2:
                print('Already prepared: {}'.format(mp4_name))
                produced += 1
                continue
        try:
            print('Transcoding {} -> {}'.format(src_path, dest_path))
            _transcode(src_path, dest_path, ffmpeg_cmd)
            print('Prepared: {}'.format(dest_path))
            produced += 1
        except subprocess.CalledProcessError as e:
            print('prepare-ambient-videos: failed to transcode {}: {}'.format(src_path, e),
                  file=sys.stderr)
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except OSError:
                    pass

    return produced


def main():
    parser = argparse.ArgumentParser(
        description='Build the Akasha OS H.264 ambient video pack.',
    )
    parser.add_argument('--out', default=DEFAULT_OUT_DIR,
                        help='Output directory for .mp4 videos.')
    parser.add_argument('--cache', default=DEFAULT_CACHE_DIR,
                        help='Cache directory for raw Commons downloads.')
    parser.add_argument('-t', '--timeout', type=int, default=180,
                        help='HTTP timeout in seconds (default: 180).')
    args = parser.parse_args()

    produced = prepare_videos(out_dir=args.out, cache_dir=args.cache,
                              timeout=args.timeout)
    if produced > 0:
        print('Prepared {} ambient video(s) in {}'.format(produced, args.out))
        return 0
    print('No ambient videos prepared.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
