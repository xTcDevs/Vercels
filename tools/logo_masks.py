"""Find the logo and metal hardware on each product photo.

Writes masks/<name>-logo.png and masks/<name>-hw.png. White items shot on marble
reuse their black twin's garment outline (same pose, cleaner cut-out).
"""
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

PHOTOS, MASKS = Path("tools/photos"), Path("tools/masks")
OUTLINE_FROM = {"zip-white": "zip-black", "shorts-white": "shorts-black", "hoodie-white": "hoodie-black"}
# Grey embroidered logos on white garments are low-contrast: use a lower threshold.
LOGO_THRESHOLD = {"hoodie-white": 45, "shorts-white": 45}
# Fixed logo regions (y0, y1, x0, x1) where auto-detection is fooled by linings or shadows.
LOGO_BOX = {"sling-black": (500, 640, 455, 585)}
# Regions kept exactly as photographed (y0, y1, x0, x1): the sling bag's metal buckle.
KEEP_BOX = {"sling-black": [(292, 470, 768, 868)]}


def luminance(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("L")).astype(float)


def box_mask(shape, box) -> np.ndarray:
    m = np.zeros(shape, bool)
    m[box[0]:box[1], box[2]:box[3]] = True
    return m


def find_logo(lum: np.ndarray, garment: np.ndarray, thresh: float, fixed_box=None) -> tuple:
    med = np.median(lum[garment])
    cand = garment & (np.abs(lum - med) > thresh)
    if fixed_box is not None:
        box = box_mask(garment.shape, fixed_box)
        return ndimage.binary_dilation(cand & box, iterations=1) & box & garment, med
    blobs, n = ndimage.label(ndimage.binary_closing(cand, iterations=6))
    if n == 0:
        raise ValueError("no logo candidates")
    best, best_count = None, 0
    for i, sl in enumerate(ndimage.find_objects(blobs), start=1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if max(h, w) / max(min(h, w), 1) > 2.6:  # long thin = zip or cord, not the logo
            continue
        count = cand[sl][blobs[sl] == i].sum()
        if count > best_count:
            best, best_count = sl, count
    if best is None:
        raise ValueError("logo not found")
    pad = 6
    box = np.zeros_like(garment)
    box[max(best[0].start - pad, 0):best[0].stop + pad, max(best[1].start - pad, 0):best[1].stop + pad] = True
    logo = cand & box
    # grow slightly to catch anti-aliased edges, then feather
    logo = ndimage.binary_dilation(logo, iterations=1) & box & garment
    return logo, med


def bbox_of(mask: np.ndarray, pad: int = 8) -> tuple:
    ys, xs = np.where(mask)
    if ys.size == 0:
        raise ValueError("empty logo mask")
    return (max(ys.min() - pad, 0), ys.max() + pad, max(xs.min() - pad, 0), xs.max() + pad)


def main() -> int:
    if not MASKS.is_dir():
        print("Error: run segment.py first", file=sys.stderr)
        return 1
    try:
        for white, black in OUTLINE_FROM.items():
            shutil.copyfile(MASKS / f"{black}-garment.png", MASKS / f"{white}-garment.png")
        found_boxes = {}
        # black twins first, so white twins can reuse their logo position
        photos = sorted(PHOTOS.glob("*.jpg"), key=lambda q: q.stem in OUTLINE_FROM)
        for p in photos:
            lum = luminance(p)
            garment = np.array(Image.open(MASKS / f"{p.stem}-garment.png")) > 128
            garment_inner = ndimage.binary_erosion(garment, iterations=4)
            fixed = LOGO_BOX.get(p.stem) or found_boxes.get(OUTLINE_FROM.get(p.stem))
            logo, med = find_logo(lum, garment_inner, LOGO_THRESHOLD.get(p.stem, 90), fixed)
            found_boxes[p.stem] = bbox_of(logo)
            hw = garment_inner & ~ndimage.binary_dilation(logo, iterations=4) & (np.abs(lum - med) > 95)
            hw = ndimage.binary_opening(hw, iterations=1)
            hw = ndimage.binary_dilation(hw, iterations=1)
            for kb in KEEP_BOX.get(p.stem, []):
                hw |= box_mask(hw.shape, kb) & garment
            for name, m in (("logo", logo), ("hw", hw)):
                img = Image.fromarray((m * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(0.8))
                img.save(MASKS / f"{p.stem}-{name}.png")
            print(f"{p.stem:20s} median L={med:5.1f} logo px={logo.sum():6d} hw px={hw.sum():6d}")
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
