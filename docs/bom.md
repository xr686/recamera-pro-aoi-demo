# Bill of Materials

| # | Item | Spec | Qty | Notes |
|---|------|------|-----|-------|
| 1 | reCamera Pro | RV1126B, reCamera OS | 1 | vision + app runtime ([Seeed Studio](https://www.seeedstudio.com/)) |
| 2 | reCamera Pro base board | with J7 10-pin MX1.25 header | 1 | provides UART4 + power |
| 3 | Seeed XIAO ESP32-C5 | MicroPython-capable dev board | 1 | turntable controller |
| 4 | DS3218 digital servo | 20 kg·cm, 50 Hz PWM | 1 | rotates the 4-slot dial |
| 5 | WS2812B LED ring | 16 pixels, 5 V | 1 | PASS/FAIL verdict indicator |
| 6 | Power supply | 5 V / 4 A, DC or screw terminal | 1 | servo + LED ring (not USB!) |
| 7 | MX1.25 cable | 10-pin or individual pigtails | 1 | J7 breakout |
| 8 | Dupont wires | F/M as needed | ~6 | XIAO ↔ J7 / servo / LED |
| 9 | Turntable dial | 4 PCB slots, 3D-printed | 1 | mounted on servo horn |
| 10 | PCB test samples | 4 boards (known component counts) | 4 | for calibration + rules |

## Optional

- USB-C cable for flashing the XIAO (data-capable).
- Small screwdriver kit for the MX1.25 connector.
- 3D printer or CNC for the dial / mount (STL generators under `model-conversion` history are not included; design your own dial to match the servo horn).

## Firmware / software (downloadable, versions pinned in this repo)

| Item | Version | Location |
|------|---------|----------|
| MicroPython for XIAO ESP32-C5 | v1.29.0 | `xiao-firmware/SEEED_XIAO_ESP32C5-v1.29.0.bin` (also on [micropython.org](https://micropython.org/download/SEEED_XIAO_ESP32C5/)) |
| AOI detection model (components34.rknn) | YOLOv8n, 34 classes, FP16 | bundled inside `camera-app/aoi-pcb-detect.tar.gz` |
| Source dataset/model | [lukemitter7/Component-Detection](https://huggingface.co/datasets/lukemitter7/Component-Detection) v.5 | see `model-conversion/` |
