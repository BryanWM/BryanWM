"""
Prepare a portrait photo for clean ASCII conversion:
  1. remove the background (rembg) so the subject is isolated
  2. boost LOCAL contrast (CLAHE) so a flatly-lit face gains highlights and
     shadows -- this is what turns a dark blob into a recognizable face
  3. composite the subject onto pure white so the background reads as blank
     (white -> spaces in the ascii ramp)
  4. crop square around the subject so the head fills the ascii frame

Output: source-prepped.png (grayscale), consumed by make_ascii_svg.py.
Run once whenever the source photo changes; the ascii SVG itself is static.

    python scripts/prep_photo.py <input.png> [output.png]
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import remove

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.png")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")

# 1. cut out the subject
cut = remove(Image.open(INP).convert("RGBA"))
rgb = np.array(cut.convert("RGB"))
alpha = np.array(cut.split()[-1])                 # 0 = background

# 2. local-contrast the luminance (CLAHE)
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8, 8))
gray = clahe.apply(gray)

# a touch of global lift so the face sits in the sparse end of the ramp
gray = cv2.convertScaleAbs(gray, alpha=1.05, beta=18)

# 3. paste onto white using the alpha mask (feathered a hair to avoid a halo)
mask = (alpha.astype(np.float32) / 255.0)
mask = cv2.GaussianBlur(mask, (0, 0), 1.0)
out = gray.astype(np.float32) * mask + 255.0 * (1.0 - mask)
out = np.clip(out, 0, 255).astype(np.uint8)

# 4. square crop around the subject's bounding box (+ a small margin)
ys, xs = np.where(alpha > 20)
side = max(xs.max() - xs.min(), ys.max() - ys.min()) + 60
cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
canvas = np.full((side, side), 255, np.uint8)
x0, y0 = cx - side // 2, cy - side // 2
sx0, sy0 = max(x0, 0), max(y0, 0)
sx1, sy1 = min(x0 + side, out.shape[1]), min(y0 + side, out.shape[0])
canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = out[sy0:sy1, sx0:sx1]
out = canvas

Image.fromarray(out, mode="L").save(OUT)
print("wrote", OUT, out.shape)
