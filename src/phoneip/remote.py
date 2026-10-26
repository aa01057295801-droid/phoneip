import asyncio
import ipaddress
import json
import time
from urllib.parse import urlparse
import requests
from .base import Rotator, RotateError
from .license import topics


def _is_ip(s):
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def check_trigger_url(url):
    """True only for https://api.pushcut.io/... (stops users making your bot call arbitrary URLs)."""
    u = urlparse(url or "")
    return u.scheme == "https" and u.hostname == "api.pushcut.io" and not u.username


class RemoteRotator(Rotator):
    """For bots on a remote host. No ADB, no open ports needed.

    1. POSTs to `trigger_url` (ntfy command topic, Pushcut execute URL, ...).
    2. The phone reconnects mobile data, then POSTs its NEW public IP
       to the ntfy topic `reply_topic`. It may first post "ack" (got the command)
       or "error: ..." (failed).
    3. This class reads that reply and returns the IP.

    on_status(str) is called from the rotating thread with
    "triggered", "ack", "got_ip" so a UI can show progress.
    """

    def __init__(self, trigger_url, reply_topic, ntfy_server="https://ntfy.sh",
                 trigger_data="rotate", trigger_headers=None, token=None,
                 timeout=90, on_status=None, **kw):
        super().__init__(**kw)
        self.trigger_url = trigger_url
        self.trigger_data = trigger_data
        self.trigger_headers = trigger_headers or {}
        self.reply_url = f"{ntfy_server.rstrip('/')}/{reply_topic}/json"
        self.auth = {"Authorization": f"Bearer {token}"} if token else {}
        self.timeout = timeout
        self.on_status = on_status
        self.last_ip = ""

    @classmethod
    def from_license(cls, license_key, trigger_url=None, ntfy_server="https://ntfy.sh", **kw):
        """Android: just the license. iPhone: also pass the Pushcut trigger_url."""
        cmd, reply = topics(license_key)
        server = ntfy_server.rstrip("/")
        return cls(trigger_url or f"{server}/{cmd}", reply, ntfy_server=server, **kw)

    def get_ip(self):
        """Last IP the phone reported (cached). Does not contact the phone."""
        return self.last_ip

    def _status(self, name):
        if self.on_status:
            try:
                self.on_status(name)
            except Exception:
                pass

    def _fetch(self, since):
        r = requests.get(self.reply_url, params={"poll": 1, "since": since},
                         headers=self.auth, timeout=15)
        r.raise_for_status()
        events = []
        for line in r.text.splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("event") == "message":
                events.append(ev)
        return events

    def _cursor(self):
        """Position just before 'now'. Uses a message id, so host/phone clock skew can't matter."""
        try:
            events = self._fetch("latest")
            if events and events[-1].get("id"):
                return events[-1]["id"]
        except requests.RequestException:
            pass
        return str(int(time.time()))

    def rotate(self, retries=2):
        old = self.last_ip
        for _ in range(retries):
            cursor = self._cursor()
            requests.post(self.trigger_url, data=self.trigger_data,
                          headers={**self.auth, **self.trigger_headers},
                          timeout=15).raise_for_status()
            self._status("triggered")
            deadline = time.time() + self.timeout
            acked = False
            same_ip = False
            while time.time() < deadline and not same_ip:
                time.sleep(3)
                for ev in self._fetch(cursor):
                    cursor = ev.get("id", cursor)
                    msg = ev.get("message", "").strip()
                    if msg.lower() == "ack":
                        if not acked:
                            acked = True
                            deadline = time.time() + self.timeout  # phone is alive: wait full time
                            self._status("ack")
                    elif msg.lower().startswith("error"):
                        raise RotateError(f"Phone reported: {msg}")
                    elif _is_ip(msg):
                        if msg != old:
                            self.last_ip = msg
                            self._status("got_ip")
                            return msg
                        same_ip = True  # same IP -> retry
        raise RotateError(f"No new IP received (last: {old or 'unknown'}). "
                          "Phone offline, automation not set up, or carrier gave same IP.")

    async def rotate_async(self, retries=2):
        """For discord.py etc.: does not block the event loop."""
        return await asyncio.to_thread(self.rotate, retries)


async def rotate_with_license(license_key, trigger_url=None, on_status=None, **kw):
    """One-liner for a bot: returns the new IP, raises RotateError / ValueError.

    on_status("triggered" | "ack" | "got_ip") is called from a worker thread.
    """
    if trigger_url and not check_trigger_url(trigger_url):
        raise ValueError("trigger_url must start with https://api.pushcut.io/")
    r = RemoteRotator.from_license(license_key, trigger_url=trigger_url, on_status=on_status, **kw)
    return await r.rotate_async()
