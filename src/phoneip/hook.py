import time
import requests
from .base import Rotator


class HttpHookRotator(Rotator):
    """iOS / any phone: call a URL that triggers a Shortcut, Tasker task, Pushcut, ntfy, etc.

    The phone-side automation must toggle airplane mode / mobile data itself.
    Because the library can't see the phone directly, the PC should be tethered
    to the phone so get_ip() reflects the phone's connection.
    """

    def __init__(self, url, method="POST", data=None, headers=None, settle_seconds=8, **kw):
        super().__init__(**kw)
        self.url, self.method, self.data = url, method, data
        self.headers, self.settle = headers or {}, settle_seconds

    def _toggle(self):
        requests.request(self.method, self.url, data=self.data,
                         headers=self.headers, timeout=15).raise_for_status()
        time.sleep(self.settle)
