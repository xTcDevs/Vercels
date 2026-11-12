"""Cut each product photo into a garment mask (masks/<name>-garment.png)."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

try:
    from rembg import new_session, remove
except ImportError:
    sys.exit("Error: rembg not installed (pip install rembg[cpu])")

PHOTOS = Path("tools/photos")
MASKS = Path("tools/masks")


def clean_mask(alpha: np.ndarray) -> np.ndarray:
    """Binarise, keep the largest object(s), fill holes, then feather the edge."""
    solid = alpha > 128
    labels, n = ndimage.label(solid)
    if n == 0:
        raise ValueError("no object found")
    sizes = ndimage.sum(solid, labels, range(1, n + 1))
    keep = np.isin(labels, [i + 1 for i, s in enumerate(sizes) if s > sizes.max() * 0.15])
    keep = ndimage.binary_closing(keep, iterations=3)
    keep = ndimage.binary_fill_holes(keep)
    soft = Image.fromarray((keep * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.2))
    return np.array(soft)


def main() -> int:
    photos = sorted(PHOTOS.glob("*.jpg"))
    if not photos:
        print(f"Error: no photos in {PHOTOS}", file=sys.stderr)
        return 1
    try:
        MASKS.mkdir(exist_ok=True)
        session = new_session("isnet-general-use")
    except Exception as e:  # model download or onnx load failure
        print(f"Error: could not start background removal: {e}", file=sys.stderr)
        return 1
    for p in photos:
        try:
            cut = remove(Image.open(p), session=session)
            mask = clean_mask(np.array(cut.split()[3]))
            Image.fromarray(mask).save(MASKS / f"{p.stem}-garment.png")
            print("ok", p.stem)
        except (OSError, ValueError) as e:
            print(f"Error on {p.name}: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
