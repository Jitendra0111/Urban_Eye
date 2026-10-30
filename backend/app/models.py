"""Loads the models once at startup. Missing weights are reported, not fatal."""
import logging

from .config import settings

log = logging.getLogger("urbaneye")


class ModelRegistry:
    def __init__(self):
        self.device = "cpu"
        self.segmenter = None
        self.detector = None

    def load(self):
        self.device = _pick_device(settings.device)
        log.info("Device: %s", self.device)

        self.segmenter = _load_segmenter(self.device)
        if self.segmenter:
            log.info("Loaded %s", self.segmenter.name)
        else:
            log.warning("Segmentation weights not found at %s; /api/segment disabled",
                        settings.seg_weights)

        want = settings.detector
        if want in ("yolo", "auto") and settings.yolo_weights.exists():
            from .services.detector import YoloDetector
            self.detector = YoloDetector(settings.yolo_weights, self.device)
        elif want in ("roboflow", "auto") and settings.roboflow_api_key:
            from .services.detector import RoboflowDetector
            self.detector = RoboflowDetector(settings.roboflow_api_key, settings.roboflow_model_id)
        if self.detector:
            log.info("Detector: %s", self.detector.name)
        else:
            log.warning("No detector: put YOLO weights at %s or set ROBOFLOW_API_KEY",
                        settings.yolo_weights)


def _load_segmenter(device: str):
    """ONNX Runtime when the exported model exists (fastest on CPU), otherwise PyTorch."""
    engine = settings.seg_engine
    use_onnx = engine == "onnx" or (engine == "auto" and device == "cpu" and settings.seg_onnx.exists())
    if use_onnx:
        try:
            from .services.segmenter import OnnxSegmenter
            return OnnxSegmenter(settings.seg_onnx, settings.seg_encoder, settings.seg_tile,
                                 settings.onnx_threads)
        except Exception as e:                     # missing onnxruntime or file: fall back
            log.warning("ONNX model not usable (%s); using PyTorch", e)
    if settings.seg_weights.exists():
        from .services.segmenter import TorchSegmenter
        return TorchSegmenter(settings.seg_weights, settings.seg_encoder, device, settings.seg_tile)
    return None


def _pick_device(choice: str) -> str:
    if choice != "auto":
        return choice
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


registry = ModelRegistry()
