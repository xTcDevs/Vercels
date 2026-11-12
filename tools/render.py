"""Render every Zaga product in every palette colour.

For each colour the source photo with the closest lightness is recoloured in
Lab space: the target colour is laid on the garment while its folds, knit and
tonal monogram are kept. Logos stay crisp and flip white/black for contrast.
Metal hardware and the background are left as photographed.

Output: zaga-website/assets/products/<product>-<colour>.webp and products.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import color

PHOTOS, MASKS = Path("tools/photos"), Path("tools/masks")
OUT = Path("assets/products")
SIZE = 800

PALETTE = {  # key: (label, hex)
    "black": ("Black", "#141414"),
    "charcoal": ("Charcoal", "#3A3A3C"),
    "stone": ("Stone", "#A9A59D"),
    "white": ("White", "#F2F2EF"),
    "sand": ("Sand", "#D6C4A1"),
    "brown": ("Brown", "#5A3A28"),
    "burgundy": ("Burgundy", "#6B1D2A"),
    "olive": ("Olive", "#5B5B34"),
    "forest": ("Forest", "#1E4A33"),
    "navy": ("Navy", "#1B2A4B"),
}

PRODUCTS = [  # id, name, category, detail, source photos (stem = <file>-<native colour>)
    ("crest-tee", "Crest Tee", "T-Shirts", "Heavyweight cotton · chest crest", ["tee-black", "tee-white"]),
    ("crest-tank", "Crest Tank", "Sleeveless", "Cotton jersey · cut-off sleeve", ["tank-black", "tank-white"]),
    ("crest-longsleeve", "Crest Long-Sleeve", "Long Sleeves", "Cotton jersey · ribbed cuffs", ["longsleeve-black", "longsleeve-white"]),
    ("crest-polo", "Crest Polo", "Polos", "Piqué cotton · embroidered crest", ["polo-charcoal"]),
    ("crest-hoodie", "Crest Hoodie", "Hoodies", "Brushed fleece · embroidered crest", ["hoodie-black", "hoodie-white", "hoodie-charcoal"]),
    ("monogram-hoodie", "Monogram Hoodie", "Hoodies", "All-over ZA monogram · centre crest", ["monohoodie-black"]),
    ("crest-zip-hoodie", "Crest Zip Hoodie", "Hoodies", "Full zip · embroidered crest", ["zip-black", "zip-white"]),
    ("crest-joggers", "Crest Joggers", "Trousers", "Fleece joggers · cuffed hem", ["joggers-black"]),
    ("monogram-joggers", "Monogram Joggers", "Trousers", "Tonal ZA monogram · cuffed hem", ["monojoggers-white"]),
    ("crest-shorts", "Crest Shorts", "Shorts", "Fleece shorts · embroidered crest", ["shorts-black", "shorts-white"]),
    ("crest-socks", "Crest Socks", "Socks", "Ribbed crew socks · embroidered crest", ["socks-black"]),
    ("crest-beanie", "Crest Beanie", "Headwear", "Rib-knit cuffed beanie", ["beanie-black"]),
    ("crest-cap", "Crest Cap", "Headwear", "Six-panel cotton cap", ["cap-black"]),
    ("monogram-sling", "Monogram Sling Bag", "Bags", "ZA monogram canvas · quick-release buckle", ["sling-black"]),
]


def load(stem: str) -> dict:
    rgb = np.array(Image.open(PHOTOS / f"{stem}.jpg").convert("RGB")).astype(float) / 255
    masks = {k: np.array(Image.open(MASKS / f"{stem}-{k}.png")).astype(float) / 255 for k in ("garment", "logo", "hw")}
    lab = color.rgb2lab(rgb)
    inner = (masks["garment"] > 0.9) & (masks["logo"] < 0.1) & (masks["hw"] < 0.1)
    logo_px = masks["logo"] > 0.5
    return {
        "stem": stem, "native": stem.rsplit("-", 1)[1], "rgb": rgb, "lab": lab, **masks,
        "L_med": float(np.median(lab[..., 0][inner])),
        "logo_light": bool(np.median(lab[..., 0][logo_px]) > np.median(lab[..., 0][inner])) if logo_px.any() else True,
    }


def recolour(src: dict, hex_colour: str) -> np.ndarray:
    target = color.rgb2lab(np.array([[[int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]]]))[0, 0]
    L_t, a_t, b_t = target
    L_s = ndimage.gaussian_filter(src["lab"][..., 0], 0.6)
    gain = 1.0 + (0.5 * L_t / 100 if src["L_med"] < 40 else 0.0)
    L_out = np.clip(L_t + (L_s - src["L_med"]) * gain, 0, 100)
    shade = np.clip(L_out / max(L_t, 1), 0.6, 1.1)
    garment_rgb = color.lab2rgb(np.dstack([L_out, a_t * shade, b_t * shade]))

    # Logo: light on dark garments, dark on light ones. Flip the photographed logo if needed.
    want_light = L_t < 55
    logo_rgb = src["rgb"]
    if want_light != src["logo_light"]:
        L_logo = 100 - src["lab"][..., 0]
        logo_rgb = color.lab2rgb(np.dstack([L_logo, np.zeros_like(L_logo), np.zeros_like(L_logo)]))

    g, lg, hw = (src[k][..., None] for k in ("garment", "logo", "hw"))
    out = src["rgb"] * (1 - g) + garment_rgb * g
    out = out * (1 - lg) + logo_rgb * lg
    out = out * (1 - hw) + src["rgb"] * hw
    return np.clip(out, 0, 1)


def save(arr: np.ndarray, path: Path) -> None:
    img = Image.fromarray((arr * 255).round().astype("uint8")).resize((SIZE, SIZE), Image.LANCZOS)
    try:
        img.save(path, "WEBP", quality=80, method=6)
    except OSError as e:
        raise OSError(f"Could not write {path}: {e}") from e


def main() -> int:
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        catalogue = []
        for pid, name, cat, detail, stems in PRODUCTS:
            sources = [load(s) for s in stems]
            colours = []
            for key, (label, hexc) in PALETTE.items():
                native = next((s for s in sources if s["native"] == key), None)
                if native is not None:
                    img = native["rgb"]
                else:
                    L_t = color.rgb2lab(np.array([[[int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]]]))[0, 0, 0]
                    src = min(sources, key=lambda s: abs(s["L_med"] - L_t))
                    img = recolour(src, hexc)
                save(img, OUT / f"{pid}-{key}.webp")
                colours.append({"key": key, "label": label, "hex": hexc,
                                "img": f"assets/products/{pid}-{key}.webp",
                                "photo": native is not None})
            default = sources[0]["native"]
            catalogue.append({"id": pid, "name": name, "category": cat, "detail": detail,
                              "defaultColour": default, "colours": colours})
            print("rendered", pid)
        (OUT.parent / "products.json").write_text(json.dumps(catalogue, indent=1))
        (OUT.parent.parent / "js" / "products.js").write_text(
            "// Generated by build/render.py — product list, categories and colour images.\n"
            "window.ZAGA_PRODUCTS = " + json.dumps(catalogue, indent=1) + ";\n")
    except (OSError, ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
