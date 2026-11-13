# xiao-firmware — XIAO ESP32-C5 turntable controller

MicroPython firmware (`main.py`, fw v0.3-c5) for the Seeed XIAO ESP32-C5.
It drives the DS3218 servo (4-station turntable) and the 16-LED WS2812B ring
(verdict indicator), and accepts line-based ASCII commands on **both** USB
serial and the UART link to the reCamera Pro.

## Files

| File | Purpose |
|------|---------|
| `main.py` | firmware — servo PWM + NeoPixel + UART command loop |
| `SEEED_XIAO_ESP32C5-v1.29.0.bin` | MicroPython v1.29.0 for XIAO ESP32-C5 |
| `flash.sh` | one-shot: erase → flash MicroPython → upload main.py → reset |
| `prep.sh` | installs esptool/mpremote/pyserial on the host PC |
| `verify.py` | sends the full command set over USB serial, reports pass count |
| `capture.py` | captures 6 s of boot output (opening the port resets the board) |

## Pin mapping (XIAO ESP32-C5)

| XIAO pin | GPIO | Function |
|----------|------|----------|
| D0 | GPIO1  | Servo PWM, 50 Hz (DS3218 signal) |
| D1 | GPIO0  | WS2812B data in (16 LEDs default) |
| D6 | GPIO11 | UART TX → reCamera Pro J7 pin 6 |
| D7 | GPIO12 | UART RX ← reCamera Pro J7 pin 5 |

> ⚠️ **The ESP32-C5 has NO UART2** (unlike classic ESP32). The firmware tries
> UART0 then UART1, remapped to GPIO11 (TX) / GPIO12 (RX) at 115200 8N1.

## Flashing

> ⚠️ **BRICK WARNING: the ESP32-C5 bootloader offset is `0x2000`.**
> Flashing the MicroPython bin at `0x0` or `0x1000` (the classic ESP32
> offset) leaves the board unbootable-looking. The provided `flash.sh`
> already uses the correct offset — if you flash manually with esptool,
> double-check it.

```bash
./prep.sh                       # once per host PC
PORT=/dev/ttyACM0 ./flash.sh    # Linux; macOS: /dev/cu.usbmodem*, Windows: COMx
```

If the board is not detected, hold **BOOT**, tap **RESET**, release BOOT to
enter download mode, then re-run.

## Command protocol (115200 8N1, one command per line, `\n` terminated)

| Command | Action | Reply |
|---------|--------|-------|
| `HELP` | list commands | usage string |
| `STATUS` | report state | `OK angle=<n> leds=<n> uart=<0\|1> fw=v0.3-c5` |
| `SERVO <0-180>` | move servo to angle | `OK SERVO <angle>` |
| `GOTO <0-3>` | move to station (0=0°, 1=60°, 2=120°, 3=180°) | `OK GOTO <i> angle=<n>` |
| `SWEEP` | sweep demo 0→60→120→180→90 | `OK SWEEP done angle=<n>` |
| `LED <idx\|ALL> <r> <g> <b>` | set LED color (0-255) | `OK LED ...` |
| `RAINBOW [cycles]` | rainbow demo | `OK RAINBOW` |
| `OFF` | all LEDs off | `OK OFF` |
| `LEDCOUNT <n>` | change LED count (default 16) | `OK LEDCOUNT <n>` |
| anything else | — | `ERR unknown cmd: ... (try HELP)` |

**Power-on self-test:** on every boot the firmware moves the servo to 90°,
runs one rainbow pass over the LED ring, blanks the LEDs, then prints
`AOI-TEST-FW v0.3 XIAO-ESP32C5 READY (type HELP)`. Seeing the rainbow at
power-up means servo + LEDs + firmware are all healthy.

## Verify from a PC (USB serial)

```bash
pip install pyserial
python3 verify.py     # runs the full command suite, prints VERIFY_RESULT: n/m passed
python3 capture.py    # just watch the boot self-test output
```
