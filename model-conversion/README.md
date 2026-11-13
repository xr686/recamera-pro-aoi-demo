# model-conversion — retrain / re-convert the detection model

You only need this folder if you want to **convert or retrain models yourself**.
The ready-to-run model (`components34.rknn`, FP16, rv1126b) is already bundled
inside `../camera-app/aoi-pcb-detect.tar.gz`.

| File | Purpose |
|------|---------|
| `MODEL-INVENTORY.md` | full inventory of the source project (MukeshSankhla/Edge-Ai-Vision-Inspection): 4 stages, weights, datasets, what is/isn't convertible |
| `RKNN-CONVERT-REPORT.md` | conversion results + pitfalls log (onnx pin, CPU torch, etc.) |
| `chain_install.sh` | reference: build a conversion venv (torch CPU → rknn-toolkit2 2.3.2 → airockchip ultralytics fork) |
| `export_all.sh` | reference: export the 4 stage weights (.pt → RKNN-compatible ONNX) |
| `convert_rknn.py` | ONNX → .rknn (rv1126b, FP16, mean 0/std 255, no quantization) |

## The model actually used in this demo

`components34.rknn` — YOLOv8n, 34 generic electronic-component classes, from
[lukemitter7/Component-Detection](https://huggingface.co/datasets/lukemitter7/Component-Detection)
v.5 (200 epochs). Exported via the airockchip ultralytics fork, converted with:

```bash
/path/to/rknn-venv/bin/python convert_rknn.py components34.onnx components34.rknn
```

## Key pitfalls (read before converting)

1. Pin **`onnx==1.15.0`** — rknn-toolkit2 2.3.2 breaks with newer onnx (`onnx.mapping` removed).
2. CPU-only torch is sufficient; conversion does not use the GPU.
3. Target platform string is `rv1126b` (reCamera Pro's NPU); keep mean 0 / std 255 and `do_quantization=False` (FP16) to match the on-board runtime (librknnrt 2.3.2).
4. Use the **airockchip/ultralytics_yolo11** fork for `yolo export format=rknn` — stock ultralytics ONNX output has a different head layout.
5. Edge Impulse `.eim` files are proprietary EON binaries and **cannot** be converted; use the `.pt` weights instead.
