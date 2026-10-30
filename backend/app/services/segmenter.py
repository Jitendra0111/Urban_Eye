"""U-Net++ land-cover segmentation (8 OpenEarthMap classes), same preprocessing as training."""
import threading
from pathlib import Path

import numpy as np

CLASS_NAMES = ["bareland", "rangeland", "developed space", "road",
               "tree", "water", "agriculture land", "building"]
PALETTE = np.array([[128, 0, 0], [0, 255, 36], [148, 148, 148], [255, 255, 255],
                    [34, 97, 38], [0, 69, 255], [75, 181, 73], [222, 31, 7]], dtype=np.uint8)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class Segmenter:
    def __init__(self, weights: Path, encoder: str, device: str, tile: int = 1024):
        import segmentation_models_pytorch as smp
        import torch

        self.torch = torch
        self.device = device
        self.tile = tile
        self.model = smp.UnetPlusPlus(encoder_name=encoder, encoder_weights=None,
                                      in_channels=3, classes=len(CLASS_NAMES))
        state = torch.load(weights, map_location=device)
        if isinstance(state, dict) and "model" in state:      # a "latest.pth" training checkpoint
            state = state["model"]
        self.model.load_state_dict(state)
        self.model.to(device).eval()
        self.lock = threading.Lock()
        self.name = f"U-Net++ ({encoder}) {Path(weights).name}"

    def _forward(self, rgb: np.ndarray) -> np.ndarray:
        """Class probabilities (C, H, W) for one tile; pads to a multiple of 32 as in training."""
        torch = self.torch
        h, w = rgb.shape[:2]
        ph, pw = (-h) % 32, (-w) % 32
        x = (rgb.astype(np.float32) / 255.0 - MEAN) / STD
        x = np.pad(x, ((0, ph), (0, pw), (0, 0)))
        t = torch.from_numpy(x.transpose(2, 0, 1)).unsqueeze(0).to(self.device)
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16,
                                                    enabled=self.device == "cuda"):
            probs = self.model(t).float().softmax(1)
            probs = (probs + self.model(t.flip(3)).float().softmax(1).flip(3)) / 2   # light TTA
        return probs[0, :, :h, :w].cpu().numpy()

    def predict(self, rgb: np.ndarray) -> np.ndarray:
        """Label map (H, W) with values 0..7. Large images are processed in overlapping tiles."""
        h, w = rgb.shape[:2]
        with self.lock:
            if max(h, w) <= self.tile:
                return self._forward(rgb).argmax(0).astype(np.uint8)
            step = self.tile - self.tile // 4
            acc = np.zeros((len(CLASS_NAMES), h, w), dtype=np.float32)
            for y in _starts(h, self.tile, step):
                for x in _starts(w, self.tile, step):
                    acc[:, y:y + self.tile, x:x + self.tile] += \
                        self._forward(rgb[y:y + self.tile, x:x + self.tile])
            return acc.argmax(0).astype(np.uint8)


def _starts(size: int, tile: int, step: int) -> list[int]:
    if size <= tile:
        return [0]
    starts = list(range(0, size - tile, step))
    return starts + [size - tile]


def coverage(labels: np.ndarray) -> dict[str, float]:
    counts = np.bincount(labels.ravel(), minlength=len(CLASS_NAMES))
    return {name: round(float(c) * 100 / labels.size, 2) for name, c in zip(CLASS_NAMES, counts)}


def colorize(labels: np.ndarray) -> np.ndarray:
    return PALETTE[labels]


def overlay(rgb: np.ndarray, labels: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    return (rgb * (1 - alpha) + PALETTE[labels] * alpha).astype(np.uint8)


def legend() -> dict[str, str]:
    return {name: "#%02x%02x%02x" % tuple(c) for name, c in zip(CLASS_NAMES, PALETTE)}
