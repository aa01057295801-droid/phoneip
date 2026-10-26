"""Android phone-side agent (run it in Termux).

First run prints a LICENSE. Paste it into the Discord bot. After that the agent
listens on a private ntfy topic; when the bot says "rotate" it toggles
airplane mode (or mobile data), then reports the new public IP.

Privilege backends (how the toggle command gets permission):
  root  - `su -c ...`                       (rooted phone)
  adb   - `adb shell ...` over wireless debugging to this same phone
  local - plain `sh -c ...`                 (only works if Termux already has the permission)
"""
import json
import os
import subprocess
import time
import requests
from .base import fetch_public_ip
from .license import generate_license, is_valid, topics

LICENSE_FILE = os.path.expanduser("~/.phoneip_license")


def load_or_create_license(path=LICENSE_FILE):
    if os.path.exists(path):
        with open(path) as f:
            key = f.read().strip()
        if is_valid(key):
            return key
    key = generate_license()
    with open(path, "w") as f:
        f.write(key + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


class AndroidAgent:
    def __init__(self, license_key, ntfy_server="https://ntfy.sh", backend="auto",
                 keep_wifi=False, method="airplane", off_seconds=3, wait_online=45,
                 retries=3, token=None):
        cmd, reply = topics(license_key)
        self.server = ntfy_server.rstrip("/")
        self.cmd_topic, self.reply_topic = cmd, reply
        self.backend = backend
        self.keep_wifi, self.method = keep_wifi, method
        self.off_seconds, self.wait_online, self.retries = off_seconds, wait_online, retries
        self.auth = {"Authorization": f"Bearer {token}"} if token else {}

    # ---- shell with privileges -------------------------------------------------
    def _run_raw(self, backend, cmd, timeout=20):
        argv = {"root": ["su", "-c", cmd],
                "adb": ["adb", "shell", cmd],
                "local": ["sh", "-c", cmd]}[backend]
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)

    def detect_backend(self):
        if self.backend != "auto":
            return self.backend
        for b, probe in (("root", "id"), ("adb", "id")):
            try:
                r = self._run_raw(b, probe, timeout=8)
                if r.returncode == 0 and "uid=" in r.stdout:
                    return b
            except (OSError, subprocess.SubprocessError):
                continue
        return "local"

    def _sh(self, cmd):
        r = self._run_raw(self.backend, cmd)
        return r.returncode == 0

    # ---- actions ----------------------------------------------------------------
    def _toggle(self):
        if self.method == "airplane":
            ok = self._sh("cmd connectivity airplane-mode enable")
            time.sleep(self.off_seconds)
            self._sh("cmd connectivity airplane-mode disable")
            if ok:
                time.sleep(3)
                return True
        # fall back / explicit data mode
        ok = self._sh("svc data disable")
        time.sleep(self.off_seconds)
        self._sh("svc data enable")
        time.sleep(3)
        return ok

    def _wait_ip(self):
        end = time.time() + self.wait_online
        while time.time() < end:
            ip = fetch_public_ip(timeout=6)
            if ip:
                return ip
            time.sleep(2)
        return ""

    def rotate_once(self):
        if not self.keep_wifi:
            # With Wi-Fi on, the "public IP" would be the Wi-Fi's, not the carrier's.
            self._sh("svc wifi disable")
            time.sleep(1)
        old = fetch_public_ip(timeout=6)
        for _ in range(self.retries):
            if not self._toggle():
                raise RuntimeError("could not toggle radio (no permission; use --backend root/adb)")
            new = self._wait_ip()
            if new and new != old:
                return new
        raise RuntimeError(f"IP did not change (still {old or 'unknown'})")

    # ---- ntfy -------------------------------------------------------------------
    def _reply(self, text):
        try:
            requests.post(f"{self.server}/{self.reply_topic}", data=text.encode(),
                          headers=self.auth, timeout=15)
        except requests.RequestException:
            pass

    def handle(self):
        self._reply("ack")
        try:
            self._reply(self.rotate_once())
        except Exception as e:  # report every failure back to the bot
            self._reply(f"error: {e}"[:200])

    def run_forever(self, once=False):
        self.backend = self.detect_backend()
        print(f"[phoneip] backend={self.backend} topic={self.cmd_topic}", flush=True)
        cursor = str(int(time.time()))
        backoff = 2
        while True:
            try:
                with requests.get(f"{self.server}/{self.cmd_topic}/json", params={"since": cursor},
                                  headers=self.auth, stream=True, timeout=(10, 120)) as r:
                    r.raise_for_status()
                    backoff = 2
                    for line in r.iter_lines():
                        if not line:
                            continue
                        ev = json.loads(line)
                        if ev.get("event") != "message":
                            continue
                        cursor = ev.get("id", cursor)
                        if ev.get("message", "").strip().lower() == "rotate":
                            self.handle()
                            if once:
                                return
            except (requests.RequestException, ValueError):
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
