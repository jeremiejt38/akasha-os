#!/usr/bin/env python3
"""Compare two screenshots: mean abs diff, SSIM-ish luminance check, and a diff image.

Usage: compare.py <ref.png> <akasha.png> [out_diff.png]
Prints metrics; writes out_diff.png (amplified) when requested.
"""
import sys

import numpy as np
from PIL import Image


def main() -> int:
    ref_path, test_path = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else None

    a = Image.open(ref_path).convert("RGB")
    b = Image.open(test_path).convert("RGB")
    if a.size != b.size:
        b = b.resize(a.size)
        print(f"note: resized test image {test_path} to {a.size}")

    pa = np.asarray(a, dtype=np.int16)
    pb = np.asarray(b, dtype=np.int16)
    diff = np.abs(pa - pb)

    mean_diff = float(diff.mean())
    max_diff = int(diff.max())
    # fraction of pixels whose max channel delta exceeds a perceptibility threshold
    per_pixel = diff.max(axis=2)
    pct_over_10 = float((per_pixel > 10).mean() * 100)
    pct_over_40 = float((per_pixel > 40).mean() * 100)

    print(f"ref   : {ref_path}")
    print(f"test  : {test_path}")
    print(f"mean|diff| = {mean_diff:.2f}  max|diff| = {max_diff}")
    print(f"pixels >10 delta: {pct_over_10:.1f}%   pixels >40 delta: {pct_over_40:.1f}%")

    if out:
        amp = np.clip(diff * 4, 0, 255).astype(np.uint8)
        Image.fromarray(amp).save(out)
        print(f"diff image written: {out} (x4 amplified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
