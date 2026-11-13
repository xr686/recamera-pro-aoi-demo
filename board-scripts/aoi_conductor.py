#!/usr/bin/env python3
"""AOI conductor: rotate tray -> sample detections -> judge -> LED verdict.

Stations/angles: /userdata/aoi-cal.json  (calibrated via :8899 UI)
Rules:           /userdata/aoi-rules.json {"1":{"ic":3,"capacitor":2},...}
                 group counts must match EXACTLY, else FAIL.
Detection source: tail aoi-pcb-detect app.log frame lines.
Verdict TX (UART4 -> XIAO fw v0.3-c5):
  PASS -> LED ALL green, hold solid
  FAIL -> LED ALL red blink x3
Stop: touch /tmp/aoi_conductor.stop
"""
import json
import os
import time
from datetime import datetime

UART = "/dev/ttyS4"
APPLOG = "/userdata/local/apps/aoi-pcb-detect/logs/app.log"
CAL = "/userdata/aoi-cal.json"
RULES = "/userdata/aoi-rules.json"
OUTLOG = "/userdata/aoi-conductor.log"
STOP = "/tmp/aoi_conductor.stop"

SETTLE_S = 3.5      # servo settle after move
SAMPLE_S = 4.0      # detection sampling window
HOLD_S = 6.0        # verdict LED hold
MIN_FRAMES = 5

GROUPS = {
    "resistor": ["Resistor", "Resistor Network", "Resistor Jumper", "Potentiometer"],
    "capacitor": ["Capacitor", "Capacitor Jumper", "Electrolytic Capacitor"],
    "inductor": ["Inductor", "Ferrite Bead", "Transformer"],
    "ic": ["IC", "iC", "Clock", "Display", "EM", "PS", "SK"],
    "diode": ["Diode", "Zener Diode", "Led"],
}
KIND_OF = {m: k for k, ms in GROUPS.items() for m in ms}

_fd = os.open(UART, os.O_WRONLY | os.O_NOCTTY)


def tx(cmd):
    os.write(_fd, (cmd.strip() + "\n").encode())
    log("TX: " + cmd)


def log(msg):
    line = "%s %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(OUTLOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def median(xs):
    if not xs:
        return 0
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def sample_frames():
    """Collect per-frame group counts from app.log for SAMPLE_S seconds."""
    try:
        pos = os.path.getsize(APPLOG)
    except OSError:
        pos = 0
    frames = []
    end = time.time() + SAMPLE_S
    with open(APPLOG, errors="replace") as f:
        f.seek(pos)
        while time.time() < end:
            line = f.readline()
            if not line:
                time.sleep(0.15)
                # handle rotation
                try:
                    if os.path.getsize(APPLOG) < pos:
                        f.seek(0)
                except OSError:
                    pass
                continue
            if "dets=" not in line:
                continue
            counts = {}
            tail = line.split("clients=", 1)[-1]
            for item in tail.strip().split(", " if ", " in tail else ","):
                item = item.strip()
                if not item or ":" not in item:
                    continue
                name = item.rsplit(":", 1)[0].strip()
                kind = KIND_OF.get(name)
                if kind:
                    counts[kind] = counts.get(kind, 0) + 1
            frames.append(counts)
    return frames


def judge(frames, rule):
    if len(frames) < MIN_FRAMES:
        return None, {}
    meds = {}
    for kind in ("ic", "capacitor", "resistor", "inductor", "diode"):
        meds[kind] = median([f.get(kind, 0) for f in frames])
    ok = True
    for kind, want in rule.items():
        if int(round(meds.get(kind, 0))) != int(want):
            ok = False
    return ok, meds


def green_hold():
    tx("LED ALL 0 200 0")


def red_blink3():
    for _ in range(3):
        tx("LED ALL 200 0 0")
        time.sleep(0.4)
        tx("OFF")
        time.sleep(0.3)


def main():
    if os.path.exists(STOP):
        os.remove(STOP)
    cal = load_json(CAL, {"slots": {}})["slots"]
    rules = load_json(RULES, {})
    log("conductor start cal=%s rules=%s" % (cal, rules))
    tx("OFF")
    while not os.path.exists(STOP):
        for st in ("1", "2", "3", "4"):
            if os.path.exists(STOP):
                break
            angle = cal.get(st)
            if angle is None:
                log("station %s not calibrated, skip" % st)
                continue
            tx("SERVO %d" % int(angle))
            log("station PCB%s -> %d deg, settling %.1fs" % (st, angle, SETTLE_S))
            time.sleep(SETTLE_S)
            frames = sample_frames()
            rule = rules.get(st, {})
            verdict, meds = judge(frames, rule)
            if verdict is None:
                log("PCB%s: insufficient frames (%d), retry once" % (st, len(frames)))
                frames = sample_frames()
                verdict, meds = judge(frames, rule)
            if verdict is None:
                log("PCB%s: NO DATA from app (frames=%d) - is aoi-pcb-detect running?" % (st, len(frames)))
                tx("LED ALL 80 40 0")   # amber = no data
                time.sleep(HOLD_S)
                tx("OFF")
                continue
            counts = {k: meds[k] for k in ("ic", "capacitor") if k in meds}
            if verdict:
                log("PCB%s PASS rule=%s counts=%s" % (st, rule, counts))
                green_hold()
            else:
                log("PCB%s FAIL rule=%s counts=%s" % (st, rule, counts))
                red_blink3()
            time.sleep(HOLD_S)
            tx("OFF")
        time.sleep(1.0)
    log("conductor stopped")
    tx("OFF")


if __name__ == "__main__":
    main()
