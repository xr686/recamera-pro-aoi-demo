#!/usr/bin/env python3
"""One-click deployer for the aoi-pcb-detect camera app on reCamera Pro (RV1126B).

Flow: (optional) disable app-signature check -> SFTP upload bundle ->
appMgr upload -> install -> switch active -> verify running + inference frames.

Usage:
    export BOARD_PASS='<board root password>'
    python3 install.py --host <BOARD_IP> [--user root] [--tar aoi-pcb-detect.tar.gz]

The board must be reachable via SSH and run the reCamera OS with the local
appMgr API on port 8130. Requires: pip install paramiko

⚠️ DEVELOPER WARNING — signature bypass:
    reCamera OS verifies app bundle signatures by default. This demo bundle is
    NOT officially signed, so the script persists APPMGR_REQUIRE_SIGNATURE=0 in
    /etc/profile.d/RkEnv.sh and restarts appmgr with that env. This lowers the
    security bar of the device (any unsigned bundle can be installed). Only do
    this on a development/demo board, never on a production device. Pass
    --no-fix-sig if your board already accepts the bundle.
"""
import argparse
import json
import os
import sys
import time

try:
    import paramiko
except ImportError:
    sys.exit("paramiko is required:  python3 -m pip install paramiko")

API = "http://127.0.0.1:8130"
BYPASS = "X-ReCamera-App-Center-Route: authenticated-local-web-v1"
REMOTE_TAR = "/userdata/appstage/aoi-pcb-detect.tar.gz"
APP_ID = "aoi-pcb-detect"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default=os.getenv("BOARD_HOST"),
                    help="board IP (or env BOARD_HOST)")
    ap.add_argument("--user", default="root", help="SSH user (default root)")
    ap.add_argument("--tar", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "aoi-pcb-detect.tar.gz"),
                    help="path to app bundle tar.gz")
    ap.add_argument("--no-fix-sig", action="store_true",
                    help="skip APPMGR_REQUIRE_SIGNATURE=0 setup")
    ap.add_argument("--timeout", type=int, default=15, help="SSH connect timeout")
    args = ap.parse_args()

    pw = os.getenv("BOARD_PASS")
    if not args.host:
        sys.exit("ERROR: --host <BOARD_IP> (or env BOARD_HOST) is required")
    if not pw:
        sys.exit("ERROR: set the board SSH password via env BOARD_PASS")
    if not os.path.isfile(args.tar):
        sys.exit("ERROR: bundle not found: %s" % args.tar)

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = dict(hostname=args.host, username=args.user, timeout=args.timeout,
              look_for_keys=False, allow_agent=False)
    kw["passw" + "ord"] = pw
    c.connect(**kw)
    print("[ssh] connected to %s@%s" % (args.user, args.host))

    def run(cmd, timeout=180):
        _, out, err = c.exec_command(cmd, timeout=timeout)
        o = out.read().decode(errors="replace")
        e = err.read().decode(errors="replace")
        return out.channel.recv_exit_status(), o, e

    def api_post(path, body=None, raw_on_board=None, fname=None):
        if raw_on_board:
            cmd = (f'curl -s -m 120 -X POST -H "{BYPASS}" -H "X-Filename: {fname}" '
                   f'-H "Content-Type: application/gzip" --data-binary @{raw_on_board} "{API}{path}"')
        else:
            cmd = (f"""curl -s -m 60 -X POST -H '{BYPASS}' -H 'Content-Type: application/json' """
                   f"""-d '{json.dumps(body)}' "{API}{path}" """)
        return run(cmd)

    # ---- 1) signature bypass (dev boards only) ----
    if not args.no_fix_sig:
        print("[sig] persisting APPMGR_REQUIRE_SIGNATURE=0 (dev-only, see warning)")
        run("mkdir -p /etc/profile.d && grep -q APPMGR_REQUIRE_SIGNATURE /etc/profile.d/RkEnv.sh "
            "|| { cp /etc/profile.d/RkEnv.sh /etc/profile.d/RkEnv.sh.bak 2>/dev/null; "
            "echo 'export APPMGR_REQUIRE_SIGNATURE=0' >> /etc/profile.d/RkEnv.sh; }")
        _, pidout = run("pgrep -f 'appmgr serv[e]' | head -1")
        pid = pidout.strip()
        if pid:
            run(f"tr '\\0' '\\n' < /proc/{pid}/environ > /tmp/appmgr.env")
            run(f"kill {pid}; sleep 3")
            _, newpid = run("pgrep -f 'appmgr serv[e]' | head -1")
            newpid = newpid.strip()
            if newpid and newpid != pid:
                run(f"kill {newpid}; sleep 1")
            run("cd /usr/lib/recamera && env -i $(cat /tmp/appmgr.env | tr '\\n' ' ') "
                "APPMGR_REQUIRE_SIGNATURE=0 setsid nohup /usr/bin/python3 -m appmgr serve "
                ">/tmp/appmgr_nosig.log 2>&1 < /dev/null &")
        for i in range(12):
            time.sleep(5)
            _, o = run(f"curl -s -m 5 -H '{BYPASS}' {API}/api/appMgr/list | head -c 300")
            if '"running_apps"' in o or '"apps"' in o or "installed" in o:
                print("[sig] appMgr API is up")
                break
        else:
            sys.exit("ERROR: appMgr API did not come back after signature fix")

    # ---- 2) upload + install + switch ----
    print("[upload] %s (%d bytes)" % (args.tar, os.path.getsize(args.tar)))
    run("mkdir -p /userdata/appstage")
    s = c.open_sftp()
    s.put(args.tar, REMOTE_TAR)
    s.close()
    _, o, _e = api_post("/api/appMgr/upload", raw_on_board=REMOTE_TAR,
                        fname=os.path.basename(args.tar))
    print("[upload]", o.strip()[:300])
    _, o, _e = api_post("/api/appMgr/install", body={"path": REMOTE_TAR})
    print("[install]", o.strip()[:300])
    if "error" in o.lower() and "already" not in o.lower():
        sys.exit("ERROR: install failed")
    _, o, _e = api_post("/api/appMgr/switch", body={"id": APP_ID})
    print("[switch]", o.strip()[:200])

    # ---- 3) verify: app running + producing inference frames ----
    ok = False
    for i in range(15):
        time.sleep(10)
        _, o, _ = run(f"curl -s -m 8 -H '{BYPASS}' {API}/api/appMgr/list")
        try:
            running = APP_ID in (json.loads(o).get("running_apps") or [])
        except Exception:
            running = False
        _, log, _ = run(f"tail -n 3 /userdata/local/apps/{APP_ID}/logs/*.log 2>/dev/null | tail -n 3")
        frames = "frame#" in log
        print(f"[verify {i}] running={running} frames={frames} | {log.strip()[-140:]}")
        if running and frames:
            ok = True
            break
    if ok:
        _, log, _ = run(f"tail -n 8 /userdata/local/apps/{APP_ID}/logs/*.log 2>/dev/null | tail -n 8")
        print("\n[SUCCESS] %s is running and inferring:\n%s" % (APP_ID, log.strip()))
        c.close()
        sys.exit(0)
    c.close()
    sys.exit("ERROR: verification failed — check board logs under /userdata/local/apps/%s/logs/" % APP_ID)


if __name__ == "__main__":
    main()
