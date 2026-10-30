"""Land-cover change between two dates: compare the U-Net++ label maps pixel by pixel."""
import numpy as np

from .segmenter import CLASS_NAMES, PALETTE

CHANGE_DIM = 0.35   # unchanged pixels are shown as a dimmed grey copy of the later image


def compare(before: np.ndarray, after: np.ndarray, after_rgb: np.ndarray, area_ha: float) -> dict:
    n = len(CLASS_NAMES)
    if before.shape != after.shape:
        raise ValueError("Label maps must have the same size")
    total = before.size
    changed = before != after

    matrix = np.bincount(before.ravel().astype(np.int64) * n + after.ravel(),
                         minlength=n * n).reshape(n, n)
    transitions = []
    for i in range(n):
        for j in range(n):
            if i != j and matrix[i, j]:
                pct = matrix[i, j] * 100 / total
                if pct >= 0.05:
                    transitions.append({"from_class": CLASS_NAMES[i], "to_class": CLASS_NAMES[j],
                                        "percent": round(pct, 2),
                                        "hectares": round(pct * area_ha / 100, 3)})
    transitions.sort(key=lambda t: -t["percent"])

    grey = after_rgb.mean(axis=2, keepdims=True) * CHANGE_DIM
    change_map = np.repeat(grey, 3, axis=2).astype(np.uint8)
    change_map[changed] = PALETTE[after[changed]]

    changed_pct = changed.sum() * 100 / total
    return {"changed_percent": round(float(changed_pct), 2),
            "changed_hectares": round(float(changed_pct * area_ha / 100), 3),
            "transitions": transitions[:12],
            "change_map": change_map}
