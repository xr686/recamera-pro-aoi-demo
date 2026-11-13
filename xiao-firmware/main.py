# AOI turntable test firmware v0.2 - XIAO ESP32C5 adapted
# Servo PWM: GPIO1 (D0) | WS2812 DIN: GPIO0 (D1) | UART2: TX=GPIO11 (D6) RX=GPIO12 (D7) @115200
# Command protocol (line-based, works on both USB serial and UART2):
#   HELP                       show help
#   STATUS                     report state
#   SERVO <0-180>              move servo to angle
#   GOTO <0-3>                 move to station (0=0deg load, 1=60, 2=120, 3=180)
#   SWEEP                      servo sweep demo
#   LED <idx|ALL> <r> <g> <b>  set LED color (0-255)
#   RAINBOW [cycles]           rainbow demo
#   OFF                        all LEDs off
#   LEDCOUNT <n>               change LED count (default 16)

from machine import Pin, PWM, UART
import neopixel
import time
import sys
import select

# === XIAO ESP32C5 pin mapping ===
SERVO_PIN = 1    # D0
LED_PIN = 0      # D1
UART_TX = 11     # D6
UART_RX = 12     # D7

STATIONS = (0, 60, 120, 180)

# ESP32-C5 has only UART0/UART1 (no UART2 like classic ESP32); try both
uart = None
for _uid in (0, 1):
    try:
        uart = UART(_uid, baudrate=115200, tx=Pin(UART_TX), rx=Pin(UART_RX))
        break
    except Exception:
        uart = None

servo = PWM(Pin(SERVO_PIN), freq=50)

led_count = 16
np = neopixel.NeoPixel(Pin(LED_PIN), led_count)
angle = -1


def set_angle(a):
    global angle
    a = max(0, min(180, int(a)))
    us = 500 + 2000 * a // 180
    servo.duty_u16(us * 65535 // 20000)
    angle = a


def init_leds(n):
    global np, led_count
    n = max(1, min(256, int(n)))
    led_count = n
    np = neopixel.NeoPixel(Pin(LED_PIN), n)


def wheel(p):
    p = p & 255
    if p < 85:
        return (p * 3, 255 - p * 3, 0)
    if p < 170:
        p -= 85
        return (255 - p * 3, 0, p * 3)
    p -= 170
    return (0, p * 3, 255 - p * 3)


def rainbow(cycles=1, wait_ms=8):
    total = cycles * 256
    step = max(1, total // 200)
    for c in range(0, total, step):
        for i in range(led_count):
            np[i] = wheel(i * 256 // led_count + c)
        np.write()
        time.sleep_ms(wait_ms)


def respond(out, msg):
    try:
        if uart is not None and out is uart:
            uart.write(msg + "\r\n")
        else:
            print(msg)
    except Exception:
        pass


def handle(line, out):
    p = line.strip().split()
    if not p:
        return
    cmd = p[0].upper()
    try:
        if cmd == "HELP":
            respond(out, "SERVO <0-180> | GOTO <0-3> | SWEEP | LED <idx|ALL> <r> <g> <b> | RAINBOW [n] | OFF | LEDCOUNT <n> | STATUS")
        elif cmd == "STATUS":
            respond(out, "OK angle=%d leds=%d uart=%d fw=v0.3-c5" % (angle, led_count, 1 if uart else 0))
        elif cmd == "SERVO":
            set_angle(int(p[1]))
            respond(out, "OK SERVO %d" % angle)
        elif cmd == "GOTO":
            i = int(p[1]) % len(STATIONS)
            set_angle(STATIONS[i])
            respond(out, "OK GOTO %d angle=%d" % (i, angle))
        elif cmd == "SWEEP":
            for a in (0, 60, 120, 180, 90):
                set_angle(a)
                time.sleep_ms(700)
            respond(out, "OK SWEEP done angle=%d" % angle)
        elif cmd == "LED":
            idx = p[1].upper()
            r, g, b = int(p[2]) & 255, int(p[3]) & 255, int(p[4]) & 255
            if idx == "ALL":
                np.fill((r, g, b))
            else:
                np[int(idx) % led_count] = (r, g, b)
            np.write()
            respond(out, "OK LED %s %d %d %d" % (idx, r, g, b))
        elif cmd == "RAINBOW":
            n = int(p[1]) if len(p) > 1 else 1
            rainbow(n)
            respond(out, "OK RAINBOW")
        elif cmd == "OFF":
            np.fill((0, 0, 0))
            np.write()
            respond(out, "OK OFF")
        elif cmd == "LEDCOUNT":
            init_leds(int(p[1]))
            respond(out, "OK LEDCOUNT %d" % led_count)
        else:
            respond(out, "ERR unknown cmd: %s (try HELP)" % cmd)
    except Exception as e:
        respond(out, "ERR %s" % e)


# ---- boot demo: servo to 90 deg + one rainbow pass ----
set_angle(90)
rainbow(1)
np.fill((0, 0, 0))
np.write()

poller = select.poll()
poller.register(sys.stdin, select.POLLIN)
bufs = {id(sys.stdin): b""}
if uart is not None:
    poller.register(uart, select.POLLIN)
    bufs[id(uart)] = b""

print("AOI-TEST-FW v0.3 XIAO-ESP32C5 READY (type HELP)")

while True:
    try:
        events = poller.poll(200)
    except KeyboardInterrupt:
        break
    for obj, ev in events:
        if not ev & select.POLLIN:
            continue
        try:
            if obj is uart:
                n = uart.any()
                data = uart.read(n) if n else b""
            else:
                data = obj.read(1)
        except Exception:
            continue
        if not data:
            continue
        key = id(obj)
        bufs[key] += data
        while b"\n" in bufs[key]:
            line, bufs[key] = bufs[key].split(b"\n", 1)
            line = line.replace(b"\r", b"").decode("utf-8", "ignore")
            if line.strip():
                handle(line, obj)
