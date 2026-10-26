import subprocess
import time
from .base import Rotator, fetch_public_ip


class AdbRotator(Rotator):
    """Android via ADB (USB or wireless).

    method: "data"     -> svc data disable/enable (no root)
            "airplane" -> cmd connectivity airplane-mode (Android 11+, no root)
    root:   run commands through `su -c` (for devices where the above need root)
    ip_source: "host"   -> check IP from this PC (when PC is tethered via the phone)
               "device" -> run curl/wget on the phone itself
    """

    def __init__(self, serial=None, method="data", root=False, ip_source="host", **kw):
        super().__init__(**kw)
        self.base = ["adb"] + (["-s", serial] if serial else [])
        self.method, self.root, self.ip_source = method, root, ip_source

    def _sh(self, cmd, timeout=15):
        if self.root:
            cmd = f"su -c '{cmd}'"
        return subprocess.run(self.base + ["shell", cmd], capture_output=True,
                              text=True, timeout=timeout)

    def get_ip(self):
        if self.ip_source == "host":
            return fetch_public_ip()
        for cmd in ("curl -s https://api.ipify.org", "wget -qO- https://api.ipify.org"):
            try:
                out = self._sh(cmd, timeout=12).stdout.strip()
                if out:
                    return out
            except subprocess.TimeoutExpired:
                pass
        return ""

    def _toggle(self):
        if self.method == "airplane":
            self._sh("cmd connectivity airplane-mode enable")
            time.sleep(self.off_seconds)
            self._sh("cmd connectivity airplane-mode disable")
        else:
            self._sh("svc data disable")
            time.sleep(self.off_seconds)
            self._sh("svc data enable")
        time.sleep(3)
