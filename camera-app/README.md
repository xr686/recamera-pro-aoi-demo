# camera-app — AOI PCB Detect (reCamera Pro native app)

Prebuilt app bundle for the reCamera Pro (RV1126B). The tarball contains
**everything**: app code (`app.py`), manifest, integrity lock files, and the
RKNN model (`models/components34.rknn`, YOLOv8n, 34 electronic-component
classes, FP16) — no separate model download needed.

## Bundle contents

```
aoi-pcb-detect.tar.gz
├── app.py               # dual-model detection app (uses components34)
├── manifest.json        # app metadata (id: aoi-pcb-detect, v0.2.0)
├── release.lock.json    # digest lock
├── files.sha256         # per-file checksums
├── icon.png
└── models/components34.rknn   # 34-class component detector (FP16)
```

sha256 (tarball): see the repository README "Release checksums" section.

## One-click install

From a PC that can SSH to the board:

```bash
pip install paramiko
export BOARD_PASS='<your board root password>'
python3 install.py --host <BOARD_IP>
```

What `install.py` does:

1. **Signature bypass (dev only)** — persists `APPMGR_REQUIRE_SIGNATURE=0` in
   `/etc/profile.d/RkEnv.sh` and restarts `appmgr` with that env (backs up the
   original file first). Skip with `--no-fix-sig` if not needed.
2. SFTP-uploads the bundle to `/userdata/appstage/`.
3. Calls the local appMgr API: `upload` → `install` → `switch` (activate).
4. Verifies for up to 150 s: app listed in `running_apps` **and** producing
   `frame#` inference lines in `/userdata/local/apps/aoi-pcb-detect/logs/app.log`.

> ⚠️ **DEVELOPER WARNING — `APPMGR_REQUIRE_SIGNATURE=0`**
> This disables app-bundle signature verification so this unsigned demo bundle
> can be installed. Any unsigned bundle would then be installable on the board.
> Use only on development/demo devices; never ship a product with this set.
> To revert: remove the `export APPMGR_REQUIRE_SIGNATURE=0` line from
> `/etc/profile.d/RkEnv.sh` (a `.bak` copy is made automatically) and reboot.

## After install

- The camera feed with detection overlays is served by the app; open the
  board's web UI (App Center → AOI PCB Detect) to view it.
- The app writes one log line per frame including `dets=` detection counts —
  `../board-scripts/aoi_conductor.py` tails this log to make PASS/FAIL
  verdicts.

## Model details

- Source: [lukemitter7/Component-Detection](https://huggingface.co/datasets/lukemitter7/Component-Detection) v.5, YOLOv8n trained 200 epochs, 34 classes.
- Converted with rknn-toolkit2 2.3.2, `target_platform="rv1126b"`, FP16 (no quantization), mean 0 / std 255.
- Class list and grouping logic: see `app.py` inside the bundle and `../model-conversion/`.
