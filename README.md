# reCamera Pro AOI Demo — 4-Station PCB Component Inspection

An end-to-end **Automated Optical Inspection (AOI)** demo built on the
[Seeed reCamera Pro](https://www.seeedstudio.com/) (RV1126B): a servo-driven
4-station turntable presents PCBs to the camera, an on-device 34-class
component detector counts parts, and a rules engine flashes **PASS (green) /
FAIL (red)** on a WS2812B ring. Everything you need to replicate it — model,
camera app, MCU firmware, board scripts, wiring, BOM — is in this repo.

> 中文简介：基于 reCamera Pro（RV1126B）的 4 工位 PCB 元件 AOI 演示。舵机转盘把
> PCB 依次转到镜头下，板端 RKNN 模型（YOLOv8n，34 类元件）检测计数，按规则判定
> 后用 WS2812B 灯环显示 PASS（绿）/ FAIL（红闪）。仓库内含相机 App 一键包
> （模型已打包）、XIAO ESP32-C5 固件、板端脚本、接线表、BOM 和模型转换资料。

## How it works

```
┌──────────────────────────────────────────────────────────────────┐
│                        reCamera Pro (RV1126B)                    │
│  aoi-pcb-detect app ── RKNN NPU inference (components34) ──► app.log │
│                              ▲                                   │
│  aoi_conductor.py  ── tails app.log, median counts vs rules      │
│        │ SERVO <angle>                     LED ALL 0 200 0 / red │
│        ▼ UART4 (/dev/ttyS4, 115200 8N1)                          │
│  aoi_cal_server.py ── web UI :8899 for servo calibration         │
└────────┼─────────────────────────────────────────────────────────┘
         ▼ 3 wires (TX/RX/GND) via base board J7
┌─────────────────────────────┐
│  XIAO ESP32-C5 (main.py)    │──PWM──► DS3218 servo ──► 4-slot turntable
│  fw v0.3-c5, MicroPython    │──DIN──► WS2812B 16-LED ring (verdict)
└─────────────────────────────┘
```

Demo loop (per round, stations 1→4): rotate servo → settle 3.5 s → sample
detector frames for 4 s → compare median component-group counts against the
station rule (exact match required) → LED verdict (PASS solid green / FAIL red
blink ×3 / no data amber) → hold 6 s → next station.

## Repository layout

| Path | Contents |
|------|----------|
| [`camera-app/`](camera-app/) | **one-click bundle** `aoi-pcb-detect.tar.gz` (app + model, 5.4 MB) and `install.py` deployer |
| [`xiao-firmware/`](xiao-firmware/) | ESP32-C5 MicroPython firmware, flashing scripts, MicroPython v1.29.0 bin |
| [`board-scripts/`](board-scripts/) | calibration web UI (:8899), demo conductor, boot autostart |
| [`model-conversion/`](model-conversion/) | how the RKNN model was produced (retrain/reconvert reference) |
| [`docs/wiring.md`](docs/wiring.md) | J7 pinout + full wiring table |
| [`docs/bom.md`](docs/bom.md) | bill of materials |

## Quick start

1. **Build the hardware** — get the parts in [`docs/bom.md`](docs/bom.md),
   wire everything per [`docs/wiring.md`](docs/wiring.md).
   ⚠️ J7 pins 7/8 carry 12–24 V — never connect them to the XIAO.
2. **Flash the XIAO ESP32-C5** (from a PC):
   ```bash
   cd xiao-firmware && ./prep.sh
   PORT=/dev/ttyACM0 ./flash.sh     # ⚠️ C5 bootloader offset is 0x2000 — use this script!
   python3 verify.py                # optional: full command self-test
   ```
   Power-cycle the XIAO: servo moves to 90° + one rainbow pass = healthy.
3. **Install the camera app** (from a PC that can SSH to the board):
   ```bash
   cd camera-app
   pip install paramiko
   export BOARD_PASS='<board root password>'
   python3 install.py --host <BOARD_IP>
   ```
   See [`camera-app/README.md`](camera-app/README.md) for the
   `APPMGR_REQUIRE_SIGNATURE=0` developer warning.
4. **Install board scripts + calibrate**:
   ```bash
   cd ../board-scripts              # see board-scripts/README.md for scp steps
   # then open http://<BOARD_IP>:8899/ and record the angle of each of the 4 stations
   ```
5. **Set inspection rules** on the board — `/userdata/aoi-rules.json`, e.g.:
   ```json
   {"1": {"ic": 3, "capacitor": 2}, "2": {"ic": 1}, "3": {}, "4": {}}
   ```
6. **Run** — `/etc/init.d/S98aoi_autostart start` (or reboot; it autostarts).
   Watch the LED ring: green = PASS, red blink = FAIL, amber = app not producing data.

## XIAO command protocol (115200 8N1, line-based)

| Command | Action |
|---------|--------|
| `SERVO <0-180>` | move servo to angle |
| `GOTO <0-3>` | move to preset station (0°/60°/120°/180°) |
| `SWEEP` | servo sweep demo |
| `LED <idx\|ALL> <r> <g> <b>` | set LED color |
| `RAINBOW [n]` | rainbow demo |
| `OFF` | LEDs off |
| `LEDCOUNT <n>` | set LED count (default 16) |
| `STATUS` | `OK angle=… leds=… uart=… fw=v0.3-c5` |
| `HELP` | list commands |

**Power-on self-test (XIAO):** servo → 90°, one rainbow pass, LEDs blank,
banner `AOI-TEST-FW v0.3 XIAO-ESP32C5 READY`. Details in
[`xiao-firmware/README.md`](xiao-firmware/README.md).

## Model

- `components34.rknn` — YOLOv8n, **34 electronic-component classes**, FP16,
  target `rv1126b`, no quantization. Bundled inside the camera-app tarball.
- Trained from [lukemitter7/Component-Detection](https://huggingface.co/datasets/lukemitter7/Component-Detection) v.5.
- Want to retrain/reconvert? See [`model-conversion/`](model-conversion/).

## Release checksums

| File | sha256 |
|------|--------|
| `camera-app/aoi-pcb-detect.tar.gz` | `aef1eaf0c20b47015f65fe1f2d45b85d0dd60875dd5e6af517ccaa914b335efb` |
| `xiao-firmware/SEEED_XIAO_ESP32C5-v1.29.0.bin` | `f4bb87c2e5fb8bd6628b53e7bf66989b30de76e36c9ca7a0953f3fbc6bccc05a` |

Verify: `sha256sum camera-app/aoi-pcb-detect.tar.gz`

## Credits & attribution

- Detection model source: [lukemitter7/Component-Detection](https://huggingface.co/datasets/lukemitter7/Component-Detection) (v.5).
- Multi-stage AOI pipeline inspiration: [MukeshSankhla/Edge-Ai-Vision-Inspection](https://github.com/MukeshSankhla/Edge-Ai-Vision-Inspection).
- MicroPython firmware base: [SEEED_XIAO_ESP32C5 port](https://micropython.org/download/SEEED_XIAO_ESP32C5/) v1.29.0.
- Hardware: Seeed Studio reCamera Pro + XIAO ESP32-C5.
