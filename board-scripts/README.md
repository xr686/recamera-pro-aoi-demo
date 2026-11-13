# board-scripts — scripts running on the reCamera Pro

These run **on the board** (reCamera OS, busybox userland), not on your PC.

| File | Install to | Purpose |
|------|-----------|---------|
| `aoi_cal_server.py` | `/userdata/aoi_cal_server.py` | servo calibration web UI on port **8899** |
| `aoi_conductor.py`  | `/userdata/aoi_conductor.py` | main demo loop: rotate → sample → judge → LED verdict |
| `S98aoi_autostart`  | `/etc/init.d/S98aoi_autostart` (chmod +x) | power-on autostart for both scripts + UART/GPIO setup |

## Install (from a PC with SSH access to the board)

```bash
scp aoi_cal_server.py aoi_conductor.py root@<BOARD_IP>:/userdata/
scp S98aoi_autostart root@<BOARD_IP>:/etc/init.d/
ssh root@<BOARD_IP> 'chmod +x /etc/init.d/S98aoi_autostart && /etc/init.d/S98aoi_autostart start'
```

## aoi_cal_server.py — calibration web UI (:8899)

Open `http://<BOARD_IP>:8899/` in a browser on the same network. Jog the
servo with a slider (±1°/±5° nudge), rotate each of the 4 PCB slots under the
camera lens, and click **📍 记录当前角度** to record the angle. Calibration is
persisted to `/userdata/aoi-cal.json`:

```json
{"slots": {"1": 45, "2": 90, "3": 135, "4": 180}}
```

Only whitelisted commands (`STATUS`, `HELP`, `SERVO 0-180`, `GOTO 0-3`) are
forwarded to the XIAO over `/dev/ttyS4`.

## aoi_conductor.py — demo loop

For each calibrated station 1→4:

1. `SERVO <angle>` over UART4, wait 3.5 s settle.
2. Tail the detection app log (`/userdata/local/apps/aoi-pcb-detect/logs/app.log`)
   for 4 s, collect per-frame component counts (needs ≥5 frames).
3. Compare median counts per group (`ic`, `capacitor`, `resistor`, `inductor`,
   `diode`) against the station rule in `/userdata/aoi-rules.json` — counts must
   match **exactly**:
   ```json
   {"1": {"ic": 3, "capacitor": 2}, "2": {"ic": 1}}
   ```
4. Verdict over UART → XIAO LED ring: **PASS** = solid green hold ·
   **FAIL** = red blink ×3 · **no app data** = amber.

Stop gracefully: `touch /tmp/aoi_conductor.stop`. Logs: `/userdata/aoi-conductor.log`.

## S98aoi_autostart — boot behavior

`start` (also runs at boot via busybox init): exports GPIO201 (external LED)
high, sets `/dev/ttyS4` to 115200 raw, starts cal server + conductor if not
already running (idempotent, /proc-scanning because busybox pgrep is unreliable).
The detection app itself is auto-restored by appmgr's boot_restore — not by
this script.

```bash
/etc/init.d/S98aoi_autostart start|stop|restart
# logs: /userdata/aoi-autostart.log, /userdata/aoi_cal_server.log, /userdata/aoi-conductor-boot.log
```
