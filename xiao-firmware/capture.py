#!/usr/bin/env python3
# 抓 ESP32 上电输出（打开串口会复位板子，6 秒内读全部）
import serial, time
import os
s = serial.Serial(os.environ.get("PORT", "/dev/ttyACM0"), 115200, timeout=1)
t0 = time.time()
buf = b""
while time.time() - t0 < 6:
    d = s.read(1024)
    if d:
        buf += d
print("BOOT_OUTPUT:")
print(buf.decode(errors="replace"))
s.close()
