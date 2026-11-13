#!/usr/bin/env python3
# ESP32 AOI 测试固件远程验证：发指令读回显，确认舵机/RGB 控制链路正常
import serial, time, sys

import os
PORT = os.environ.get("PORT", "/dev/ttyACM0")
s = serial.Serial(PORT, 115200, timeout=2)
# 打开串口会复位板子：先抓 6 秒上电输出（含开机自检演示）
t0 = time.time()
boot = b""
while time.time() - t0 < 6:
    d = s.read(1024)
    if d:
        boot += d
print("BOOT:", boot.decode(errors="replace").strip()[-300:])
s.reset_input_buffer()

def cmd(c, wait=0.6):
    s.write((c + "\n").encode())
    time.sleep(wait)
    out = s.read(300).decode(errors="replace").strip()
    print(f"{c!r} -> {out!r}")
    return out

ok = 0
total = 0
def check(c, expect="OK", wait=0.6):
    global ok, total
    total += 1
    r = cmd(c, wait)
    if expect in r:
        ok += 1

check("HELP")
check("STATUS")
check("SERVO 60")
time.sleep(1.0)
check("SERVO 120")
time.sleep(1.0)
check("SERVO 90")
check("GOTO 1")   # 60° 工位
time.sleep(0.8)
check("GOTO 0")   # 回 0° 工位
check("RAINBOW 1", wait=3.0)
check("LED ALL 0 255 0")   # 绿
time.sleep(1.0)
check("LED ALL 0 0 255")   # 蓝
time.sleep(1.0)
check("LED ALL 255 0 0")   # 红
time.sleep(1.0)
check("OFF")
check("STATUS")

s.close()
print(f"VERIFY_RESULT: {ok}/{total} passed")
sys.exit(0 if ok == total else 1)
