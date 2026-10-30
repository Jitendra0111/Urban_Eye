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


def load_torch_model(weights: Path, encoder: str, device: str):
    """U-Net++ with the trained weights (a plain state_dict or a training checkpoint)."""
    import segmentation_models_pytorch as smp
    import torch

    model = smp.UnetPlusPlus(encoder_name=encoder, encoder_weights=None,
                             in_channels=3, classes=len(CLASS_NAMES))
    state = torch.load(weights, map_location=device)
    if isinstance(state, dict) and "model" in state:      # a "latest.pth" training checkpoint
        state = state["model"]
    model.load_state_dict(state)
    return model.to(device).eval()


class Segmenter:
    """Shared preprocessing, tiling and test-time augmentation. Subclasses run the network.

    predict(rgb, tta=True)  -> "Accurate": averages the image and its mirror image (2 passes).
    predict(rgb, tta=False) -> "Fast": one pass, about half the time.
    """
    name = "segmenter"

    def __init__(self, tile: int = 1024):
        self.tile = tile
        self.lock = threading.Lock()

    def _logits(self, x: np.ndarray) -> np.ndarray:
        """(1, 3, H, W) float32 normalised image -> (1, C, H, W) logits."""
        raise NotImplementedError

    def _forward(self, rgb: np.ndarray, tta: bool) -> np.ndarray:
        """Class probabilities (C, H, W) for one tile; pads to a multiple of 32 as in training."""
        h, w = rgb.shape[:2]
        ph, pw = (-h) % 32, (-w) % 32
        x = (rgb.astype(np.float32) / 255.0 - MEAN) / STD
        x = np.pad(x, ((0, ph), (0, pw), (0, 0)))
        x = np.ascontiguousarray(x.transpose(2, 0, 1)[None])
        probs = _softmax(self._logits(x))
        if tta:
            flipped = np.ascontiguousarray(x[..., ::-1])
            probs = (probs + _softmax(self._logits(flipped))[..., ::-1]) / 2
        return probs[0, :, :h, :w]

    def predict(self, rgb: np.ndarray, tta: bool = True) -> np.ndarray:
        """Label map (H, W) with values 0..7. Large images are processed in overlapping tiles."""
        h, w = rgb.shape[:2]
        with self.lock:
            if max(h, w) <= self.tile:
                return self._forward(rgb, tta).argmax(0).astype(np.uint8)
            step = self.tile - self.tile // 4
            acc = np.zeros((len(CLASS_NAMES), h, w), dtype=np.float32)
            for y in _starts(h, self.tile, step):
                for x in _starts(w, self.tile, step):
                    acc[:, y:y + self.tile, x:x + self.tile] +=                         self._forward(rgb[y:y + self.tile, x:x + self.tile], tta)
            return acc.argmax(0).astype(np.uint8)


class TorchSegmenter(Segmenter):
    def __init__(self, weights: Path, encoder: str, device: str, tile: int = 1024):
        import torch

        super().__init__(tile)
        self.torch = torch
        self.device = device
        self.model = load_torch_model(weights, encoder, device)
        self.name = f"U-Net++ ({encoder}) {Path(weights).name} [PyTorch]"

    def _logits(self, x: np.ndarray) -> np.ndarray:
        torch = self.torch
        t = torch.from_numpy(x).to(self.device)
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16,
                                                    enabled=self.device == "cuda"):
            return self.model(t).float().cpu().numpy()


class OnnxSegmenter(Segmenter):
    """Same network exported with scripts/export_onnx.py, run with ONNX Runtime (faster on CPU)."""

    def __init__(self, onnx_path: Path, encoder: str, tile: int = 1024, threads: int = 0):
        import onnxruntime as ort

        super().__init__(tile)
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        if threads:
            opts.intra_op_num_threads = threads
        self.session = ort.InferenceSession(str(onnx_path), opts, providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0].name
        self.name = f"U-Net++ ({encoder}) {Path(onnx_path).name} [ONNX Runtime]"

    def _logits(self, x: np.ndarray) -> np.ndarray:
        return self.session.run(None, {self.input: x})[0]


def _softmax(logits: np.ndarray) -> np.ndarray:
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


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
