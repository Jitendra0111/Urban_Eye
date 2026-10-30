"""Image decoding / encoding helpers."""
import base64
import io

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 100_000_000   # large aerial tiles are fine, decompression bombs are not


class InvalidImage(ValueError):
    pass


def decode_image(data: bytes) -> np.ndarray:
    """Upload bytes -> RGB uint8 array (EXIF rotation applied)."""
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise InvalidImage(f"Not a readable image: {e}") from e
    return np.asarray(img)


def to_data_url(rgb: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
