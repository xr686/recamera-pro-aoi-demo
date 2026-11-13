#!/bin/bash
# One-shot flasher for XIAO ESP32-C5 AOI firmware.
#   1) erase flash  2) write MicroPython (SEEED_XIAO_ESP32C5 bin @ 0x2000)
#   3) upload main.py  4) reset & run
# Prereq: python3 -m pip install --user esptool mpremote
# Usage:  PORT=/dev/ttyACM0 ./flash.sh   (Linux default may be /dev/ttyACM0 or /dev/ttyUSB0)
set -e
cd "$(dirname "$0")"
PORT=${PORT:-/dev/ttyACM0}
BIN=SEEED_XIAO_ESP32C5-v1.29.0.bin
# esptool / mpremote: prefer PATH, fall back to python -m
ESPTOOL=$(command -v esptool || echo "python3 -m esptool")
MPREMOTE=$(command -v mpremote || echo "$HOME/.local/bin/mpremote")

if [ ! -e "$PORT" ]; then echo "Serial port $PORT not found. Set PORT=/dev/ttyXXX and retry."; exit 1; fi
if [ ! -w "$PORT" ]; then echo "No write permission on $PORT. Try: sudo usermod -aG dialout $USER (re-login), or sudo chmod a+rw $PORT"; exit 1; fi

# ⚠️ ESP32-C5 bootloader offset is 0x2000 — flashing at 0x0/0x1000 BRICKS the boot ROM layout.
echo "== 1/4 erase flash =="
$ESPTOOL --chip esp32c5 --port "$PORT" --baud 460800 erase_flash
echo "== 2/4 write MicroPython: $BIN @ 0x2000 =="
$ESPTOOL --chip esp32c5 --port "$PORT" --baud 460800 --before default_reset --after hard_reset \
  write_flash -z --flash_mode dio --flash_freq 80m --flash_size 8MB 0x2000 "$BIN"
sleep 3
echo "== 3/4 upload main.py =="
$MPREMOTE connect "$PORT" fs cp main.py :main.py
echo "== 4/4 reset & run =="
$MPREMOTE connect "$PORT" reset
echo "== FLASH DONE =="
