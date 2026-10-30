"""Export the trained U-Net++ weights to ONNX for faster CPU inference with ONNX Runtime.

Run from the backend folder (once, and again whenever you replace the .pth file):
    python scripts/export_onnx.py
It reads SEG_WEIGHTS / SEG_ENCODER from .env and writes SEG_ONNX (default models/unetpp_oem8.onnx),
then checks that ONNX Runtime gives the same predictions as PyTorch.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings                      # noqa: E402
from app.services.segmenter import CLASS_NAMES, load_torch_model  # noqa: E402


def main():
    import onnxruntime as ort
    import torch

    model = load_torch_model(settings.seg_weights, settings.seg_encoder, "cpu")
    dummy = torch.randn(1, 3, 512, 512)
    out = settings.seg_onnx
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"Exporting {settings.seg_weights.name} -> {out} ...")
    t0 = time.time()
    torch.onnx.export(model, dummy, str(out), dynamo=False, opset_version=17,
                      input_names=["image"], output_names=["logits"],
                      dynamic_axes={"image": {0: "batch", 2: "height", 3: "width"},
                                    "logits": {0: "batch", 2: "height", 3: "width"}})
    print(f"Done in {time.time() - t0:.0f} s, {out.stat().st_size / 1e6:.0f} MB")

    # Same predictions? Compare on a random-looking image of a non-square size.
    x = torch.from_numpy(np.random.default_rng(0).normal(size=(1, 3, 384, 640)).astype(np.float32))
    with torch.inference_mode():
        ref = model(x).numpy()
    sess = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"])
    got = sess.run(None, {"image": x.numpy()})[0]
    agree = (ref.argmax(1) == got.argmax(1)).mean() * 100
    print(f"Output shape {got.shape} ({len(CLASS_NAMES)} classes); max difference "
          f"{np.abs(ref - got).max():.2e}; same predicted class for {agree:.2f}% of pixels")
    if agree < 99.5:
        raise SystemExit("ONNX predictions differ from PyTorch; do not use this file.")
    print("OK. Restart the backend to use the ONNX model.")


if __name__ == "__main__":
    main()
