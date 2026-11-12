"""Cut a white printed logo out of a photo into transparent PNGs (white and black versions)."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, UnidentifiedImageError


def load_grayscale(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"Source image not found: {path}")
    try:
        with Image.open(path) as im:
            return np.array(im.convert("L")).astype(float)
    except UnidentifiedImageError as e:
        raise ValueError(f"Not a readable image: {path}") from e


def build_alpha_mask(gray: np.ndarray) -> Image.Image:
    alpha = np.clip((gray - 95) / (170 - 95), 0, 1)
    mask = Image.fromarray((alpha * 255).astype("uint8")).filter(ImageFilter.MedianFilter(5))
    mask = mask.point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.GaussianBlur(1.2))
    arr = np.array(mask) > 128
    rows = np.where(arr.sum(1) > 3)[0]
    cols = np.where(arr.sum(0) > 3)[0]
    if rows.size == 0 or cols.size == 0:
        raise ValueError("No logo found: the image has no bright printed area.")
    pad = 8
    box = (max(cols.min() - pad, 0), max(rows.min() - pad, 0),
           min(cols.max() + pad, mask.width), min(rows.max() + pad, mask.height))
    return mask.crop(box)


def save_logo(mask: Image.Image, color: tuple, out_path: Path) -> None:
    logo = Image.new("RGBA", mask.size, color + (0,))
    logo.putalpha(mask)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        logo.save(out_path)
    except OSError as e:
        raise OSError(f"Could not write {out_path}: {e}") from e


def save_logo_on_background(logo: Image.Image, size: tuple, fill: float, out_path: Path) -> None:
    """Centre the logo on a dark canvas of `size`, scaled to `fill` of it (favicon, share image)."""
    canvas = Image.new("RGB", size, (14, 13, 12))
    scale = min(size[0] * fill / logo.width, size[1] * fill / logo.height)
    resized = logo.resize((int(logo.width * scale), int(logo.height * scale)), Image.LANCZOS)
    canvas.paste(resized, ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2), resized)
    try:
        canvas.save(out_path)
    except OSError as e:
        raise OSError(f"Could not write {out_path}: {e}") from e


def main(src: str, out_dir: str = ".") -> int:
    try:
        mask = build_alpha_mask(load_grayscale(Path(src)))
        out = Path(out_dir)
        save_logo(mask, (255, 255, 255), out / "logo-white.png")
        save_logo(mask, (14, 13, 12), out / "logo-black.png")
        with Image.open(out / "logo-white.png") as white:
            white.load()
            save_logo_on_background(white, (128, 128), 0.8, out / "favicon.png")
            save_logo_on_background(white, (1200, 630), 0.6, out / "logo-black-bg.png")
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"Saved logo-white.png, logo-black.png, favicon.png and logo-black-bg.png to {out.resolve()}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_logo.py <photo> [out_dir]", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(*sys.argv[1:3]))
