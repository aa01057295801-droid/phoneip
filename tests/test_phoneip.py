import asyncio, json, unittest
from unittest import mock
from phoneip import RemoteRotator, RotateError, generate_license, is_valid_license, license_topics, check_trigger_url, rotate_with_license
import phoneip.remote as remote


class FakeNtfy:
    """Minimal ntfy: stores messages per topic; phone reply is injected on trigger."""
    def __init__(self, replies):
        self.msgs, self.n, self.replies = {}, 0, list(replies)
    def post(self, url, data=None, headers=None, timeout=None):
        topic = url.rsplit("/", 1)[1]
        if topic.startswith("pip-c-"):                 # bot -> phone: phone answers
            reply_topic = topic.replace("pip-c-", "pip-r-")
            for m in self.replies.pop(0):
                self._add(reply_topic, m)
        else:
            self._add(topic, data.decode() if isinstance(data, bytes) else data)
        r = mock.Mock(); r.raise_for_status = lambda: None; return r
    def _add(self, topic, msg):
        self.n += 1
        self.msgs.setdefault(topic, []).append({"id": f"id{self.n}", "event": "message", "message": msg})
    def get(self, url, params=None, headers=None, timeout=None):
        topic = url.rsplit("/", 2)[1]
        ev = self.msgs.get(topic, [])
        since = params["since"]
        if since == "latest": out = ev[-1:]
        elif since.startswith("id"): out = [e for e in ev if int(e["id"][2:]) > int(since[2:])]
        else: out = ev
        r = mock.Mock(); r.raise_for_status = lambda: None
        r.text = "\n".join(json.dumps(e) for e in out); return r


def patched(fake):
    return mock.patch.multiple(remote.requests, post=fake.post, get=fake.get), mock.patch.object(remote.time, "sleep", lambda s: None)


class T(unittest.TestCase):
    def test_license(self):
        k = generate_license(); self.assertTrue(is_valid_license(k))
        c, r = license_topics(k); self.assertTrue(c.startswith("pip-c-") and r.startswith("pip-r-"))
        self.assertFalse(is_valid_license("PIP-short")); self.assertFalse(is_valid_license("x"*30))
        with self.assertRaises(ValueError): license_topics("nope")

    def test_url_check(self):
        self.assertTrue(check_trigger_url("https://api.pushcut.io/k/execute?shortcut=R"))
        for bad in ("http://api.pushcut.io/x", "https://evil.com/x", "https://api.pushcut.io@evil.com/x", "https://x@api.pushcut.io/", ""):
            self.assertFalse(check_trigger_url(bad), bad)

    def test_rotate_ack_then_ip_and_status(self):
        fake = FakeNtfy([["ack", "1.2.3.4"]]); seen = []
        k = generate_license(); r = RemoteRotator.from_license(k, on_status=seen.append)
        p1, p2 = patched(fake)
        with p1, p2: self.assertEqual(r.rotate(), "1.2.3.4")
        self.assertEqual(seen, ["triggered", "ack", "got_ip"])

    def test_same_ip_retries_then_new(self):
        fake = FakeNtfy([["1.1.1.1"], ["1.1.1.1"], ["2.2.2.2"]])
        r = RemoteRotator.from_license(generate_license(), timeout=9); r.last_ip = "1.1.1.1"
        p1, p2 = patched(fake)
        with p1, p2: self.assertEqual(r.rotate(retries=3), "2.2.2.2")

    def test_stale_old_replies_ignored(self):
        fake = FakeNtfy([["9.9.9.9"]]); k = generate_license(); c, rt = license_topics(k)
        fake._add(rt, "5.5.5.5")                          # old reply from a previous run
        r = RemoteRotator.from_license(k)
        p1, p2 = patched(fake)
        with p1, p2: self.assertEqual(r.rotate(), "9.9.9.9")

    def test_error_and_timeout(self):
        k = generate_license(); p1, p2 = patched(FakeNtfy([["ack", "error: no permission"]]))
        with p1, p2, self.assertRaises(RotateError): RemoteRotator.from_license(k).rotate()
        p1, p2 = patched(FakeNtfy([[], []]))
        r = RemoteRotator.from_license(k, timeout=0)
        with p1, p2, self.assertRaises(RotateError): r.rotate()

    def test_async_helper(self):
        fake = FakeNtfy([["7.7.7.7"]]); p1, p2 = patched(fake)
        with p1, p2: self.assertEqual(asyncio.run(rotate_with_license(generate_license())), "7.7.7.7")
        with self.assertRaises(ValueError): asyncio.run(rotate_with_license(generate_license(), "https://evil.com/x"))


if __name__ == "__main__":
    unittest.main()
