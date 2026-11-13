#!/bin/bash
# Prepare a host PC for flashing the XIAO ESP32-C5 (no root needed).
# Installs esptool + mpremote into the user site, verifies versions.
cd "$(dirname "$0")" || exit 1
chmod +x flash.sh
echo "== pip install esptool mpremote pyserial =="
python3 -m pip install --user -q esptool mpremote pyserial 2>&1 | tail -3
echo "== verify tools =="
python3 -m esptool version 2>&1 | head -2
python3 -m mpremote version 2>&1 | head -1
python3 -c "import serial; print('pyserial', serial.VERSION)"
echo "== firmware bin =="
ls -la SEEED_XIAO_ESP32C5-v1.29.0.bin 2>/dev/null || \
  echo "Missing! Download from https://micropython.org/download/SEEED_XIAO_ESP32C5/"
echo PREP_DONE
