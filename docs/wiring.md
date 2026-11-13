# Wiring Guide — reCamera Pro ↔ XIAO ESP32-C5

UART link between the reCamera Pro base board and the XIAO ESP32-C5 turntable controller.

## reCamera Pro base board J7 (10-pin, MX1.25)

| Pin | Function | Note |
|-----|----------|------|
| 1–4 | CAN | not used in this demo |
| 5   | UART4_TX (GPIO5_A2) | board → XIAO (RX side) |
| 6   | UART4_RX (GPIO5_A5) | board ← XIAO (TX side) |
| 7–8 | 12–24 V power | ⚠️ **HIGH VOLTAGE — NEVER connect these to the XIAO** |
| 9   | GND | common ground |
| 10  | spare | — |

On the board side, UART4 appears as `/dev/ttyS4` (115200 8N1, raw).

Reference photos: [J7 / EXT header](images/ext_small.jpg) · [base board pins](images/base_small.jpg) · [UART debug pins](images/DEBUG_UART_PIN.jpg) · [EXT GPIO](images/EXT_GPIO.jpg)

## XIAO ESP32-C5 side

| XIAO pin | GPIO | Function | Connect to |
|----------|------|----------|-----------|
| D7 | GPIO12 | UART RX | J7 pin 5 (UART4_TX) |
| D6 | GPIO11 | UART TX | J7 pin 6 (UART4_RX) |
| D0 | GPIO1  | Servo PWM (50 Hz) | DS3218 signal (orange) |
| D1 | GPIO0  | WS2812 data in | LED ring DIN |
| 5V | — | servo + LED power | external 5 V 4 A supply (+) |
| GND | — | common ground | external supply (−) **and** J7 pin 9 |

> ⚠️ The ESP32-C5 has **no UART2** (unlike classic ESP32). The firmware uses
> UART0/UART1 remapped to GPIO11 (TX) / GPIO12 (RX). Do not wire to the
> default UART0 pads (GPIO16/17-style pins of older boards).

## Connection summary

```
reCamera Pro J7 pin5 (UART4_TX) ──► XIAO D7 (GPIO12 RX)
reCamera Pro J7 pin6 (UART4_RX) ◄── XIAO D6 (GPIO11 TX)
reCamera Pro J7 pin9 (GND)      ─── XIAO GND ─── PSU GND   (three-way common ground)
XIAO 5V                         ─── PSU 5V (+)
DS3218: orange=D0(GPIO1), red=PSU 5V, brown=PSU GND
WS2812B ring: DIN=D1(GPIO0), VCC=PSU 5V, GND=PSU GND
```

- Baud rate: **115200, 8N1**, no flow control, line-based ASCII protocol.
- J7 pins 7/8 carry 12–24 V — double-check before plugging anything in.
- Power the servo + LED ring from the external 5 V 4 A supply, **not** from the
  XIAO USB/3V3 rail (stall current will brown out the MCU).
