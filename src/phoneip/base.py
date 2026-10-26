import time
import requests

IP_URLS = ["https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"]


class RotateError(RuntimeError):
    pass


def fetch_public_ip(timeout=8):
    """Public IP of the machine running this code (use when tethered to the phone)."""
    for url in IP_URLS:
        try:
            r = requests.get(url, timeout=timeout)
            if r.ok and r.text.strip():
                return r.text.strip()
        except requests.RequestException:
            continue
    return ""


class Rotator:
    """Base class. Subclasses implement _toggle(); get_ip() may be overridden."""

    def __init__(self, off_seconds=3, wait_online=40):
        self.off_seconds = off_seconds
        self.wait_online = wait_online

    def get_ip(self) -> str:
        return fetch_public_ip()

    def _toggle(self):
        raise NotImplementedError

    def _wait_for_ip(self):
        end = time.time() + self.wait_online
        while time.time() < end:
            ip = self.get_ip()
            if ip:
                return ip
            time.sleep(2)
        return ""

    def rotate(self, retries=3) -> str:
        """Reconnect mobile data and return the new IP. Raises RotateError if unchanged."""
        old = self.get_ip()
        for _ in range(retries):
            self._toggle()
            new = self._wait_for_ip()
            if new and new != old:
                return new
        raise RotateError(f"IP did not change (still {old or 'unknown'}). Carrier may use CGNAT or reassign the same IP.")
