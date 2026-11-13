#!/usr/bin/env python3
"""AOI servo calibration web UI for reCamera Pro.

Serves a small HTML page on :8899 that controls XIAO (fw v0.3-c5) over
/dev/ttyS4 (UART4, 115200 8N1). Lets the operator jog the servo and record
the angle for each of the 4 PCB slots on the dial.

Calibration persists in /userdata/aoi-cal.json:
  {"slots": {"1": 45, "2": 90, "3": 135, "4": 180}}
"""
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 8899
DEV = "/dev/ttyS4"
CAL = "/userdata/aoi-cal.json"
_lock = threading.Lock()

subprocess.run(["stty", "-F", DEV, "115200", "raw", "-echo", "-echoe", "-echok"],
               check=False)
_fd = os.open(DEV, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)


def _drain():
    out = b""
    try:
        while True:
            chunk = os.read(_fd, 4096)
            if not chunk:
                break
            out += chunk
    except (BlockingIOError, OSError):
        pass
    return out


def uart_cmd(line, wait=2.0):
    with _lock:
        _drain()  # drop stale bytes
        os.write(_fd, (line.strip() + "\n").encode())
        out = b""
        deadline = time.time() + wait
        while time.time() < deadline:
            time.sleep(0.05)
            out += _drain()
            if b"\n" in out:
                break
        return out.decode(errors="replace").strip()


def load_cal():
    try:
        with open(CAL) as f:
            return json.load(f)
    except Exception:
        return {"slots": {}}


def save_cal(data):
    with open(CAL, "w") as f:
        json.dump(data, f)


PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AOI 舵机标定</title>
<style>
 body{font-family:system-ui,-apple-system,sans-serif;background:#111;color:#eee;
      max-width:640px;margin:0 auto;padding:16px}
 h1{font-size:20px;color:#4caf50}
 .card{background:#1e1e1e;border-radius:12px;padding:16px;margin-bottom:14px}
 input[type=range]{width:100%}
 .big{font-size:28px;font-weight:bold;color:#ffd54f}
 button{background:#2e7d32;color:#fff;border:0;border-radius:8px;
        padding:10px 14px;font-size:15px;margin:4px 2px;cursor:pointer}
 button:active{background:#1b5e20}
 button.sec{background:#37474f}
 button.go{background:#1565c0}
 .slot{display:flex;align-items:center;gap:8px;margin:8px 0;flex-wrap:wrap}
 .slot .name{width:70px;font-weight:bold}
 .slot .ang{width:60px;color:#ffd54f}
 #log{background:#000;border-radius:8px;padding:10px;font-family:monospace;
      font-size:12px;height:120px;overflow-y:auto;color:#8bc34a;white-space:pre-wrap}
 .row{display:flex;gap:6px;flex-wrap:wrap;justify-content:center}
</style>
</head>
<body>
<h1>🎛 AOI 舵机标定台</h1>

<div class="card">
 <div>当前角度: <span class="big" id="cur">--</span>°</div>
 <input type="range" id="slider" min="0" max="180" value="90">
 <div class="row">
  <button class="sec" onclick="nudge(-5)">-5</button>
  <button class="sec" onclick="nudge(-1)">-1</button>
  <button onclick="moveSlider()">▶ 转到滑条角度</button>
  <button class="sec" onclick="nudge(1)">+1</button>
  <button class="sec" onclick="nudge(5)">+5</button>
 </div>
 <div class="row">
  <button class="sec" onclick="setA(0)">0°</button>
  <button class="sec" onclick="setA(60)">60°</button>
  <button class="sec" onclick="setA(90)">90°</button>
  <button class="sec" onclick="setA(120)">120°</button>
  <button class="sec" onclick="setA(180)">180°</button>
 </div>
</div>

<div class="card">
 <b>4 个 PCB 工位标定</b>
 <div style="font-size:12px;color:#999;margin:4px 0">
  用上面滑条把目标 PCB 转到镜头正下方 → 点对应工位的「📍记录当前角度」
 </div>
 <div id="slots"></div>
</div>

<div class="card">
 <b>串口日志</b>
 <div id="log"></div>
</div>

<script>
let slots = {};
const $ = id => document.getElementById(id);

async function cmd(c){
  $('log').textContent += '> ' + c + '\\n';
  $('log').scrollTop = 1e9;
  try{
    const r = await fetch('/api/cmd?c=' + encodeURIComponent(c));
    const j = await r.json();
    if(j.resp) { $('log').textContent += j.resp + '\\n'; $('log').scrollTop = 1e9; }
    return j.resp || '';
  }catch(e){ $('log').textContent += 'ERR ' + e + '\\n'; return ''; }
}

function move(a){
  a = Math.max(0, Math.min(180, Math.round(a)));
  $('slider').value = a; $('cur').textContent = a;
  return cmd('SERVO ' + a);
}
function moveSlider(){ move(+$('slider').value); }
function nudge(d){ move(+$('slider').value + d); }
function setA(a){ move(a); }

function renderSlots(){
  let h = '';
  for(let i=1;i<=4;i++){
    const a = slots[i];
    h += `<div class="slot"><span class="name">PCB ${i}</span>
      <span class="ang">${a===undefined?'未标定':a+'°'}</span>
      <button onclick="rec(${i})">📍 记录当前角度</button>
      <button class="go" onclick="goto(${i})" ${a===undefined?'disabled':''}>🎯 转到工位</button></div>`;
  }
  $('slots').innerHTML = h;
}

async function rec(i){
  const a = +$('slider').value;
  slots[i] = a;
  await fetch('/api/cal', {method:'POST', body: JSON.stringify({slots})});
  renderSlots();
  $('log').textContent += `✓ PCB${i} 标定 = ${a}°\\n`;
}
async function goto(i){
  const a = slots[i];
  if(a===undefined) return;
  await move(a);
}
async function loadCal(){
  try{
    const r = await fetch('/api/cal'); const j = await r.json();
    slots = j.slots || {};
  }catch(e){}
  renderSlots();
}
$('slider').addEventListener('input', e => $('cur').textContent = e.target.value);
loadCal();
cmd('STATUS');
</script>
</body>
</html>
"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if u.path == "/api/cmd":
            c = parse_qs(u.query).get("c", [""])[0]
            # only allow known safe commands
            ok = False
            parts = c.split()
            if parts:
                head = parts[0].upper()
                if head in ("STATUS", "HELP"):
                    ok = True
                elif head == "SERVO" and len(parts) == 2 and parts[1].isdigit() \
                        and 0 <= int(parts[1]) <= 180:
                    ok = True
                elif head == "GOTO" and len(parts) == 2 and parts[1] in "0123":
                    ok = True
            if not ok:
                return self._send(400, json.dumps({"error": "bad cmd"}))
            return self._send(200, json.dumps({"resp": uart_cmd(c)}))
        if u.path == "/api/cal":
            return self._send(200, json.dumps(load_cal()))
        return self._send(404, json.dumps({"error": "nf"}))

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/cal":
            n = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(n))
                slots = {}
                for k, v in (data.get("slots") or {}).items():
                    if str(k) in "1234" and isinstance(v, int) and 0 <= v <= 180:
                        slots[str(k)] = v
                save_cal({"slots": slots})
                return self._send(200, json.dumps({"ok": True}))
            except Exception as e:
                return self._send(400, json.dumps({"error": str(e)}))
        return self._send(404, json.dumps({"error": "nf"}))


if __name__ == "__main__":
    with open("/tmp/aoi_cal.pid", "w") as f:
        f.write(str(os.getpid()))
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print("listening on :%d" % PORT, flush=True)
    srv.serve_forever()
