"""License = a random secret shared by the phone and the bot.

The phone (Termux agent / iPhone Shortcut) creates it on first run and shows it.
The bot user pastes it in. Both sides derive the same private ntfy topics from it,
so no server of your own is needed. Treat the license like a password: whoever has it
can trigger the phone and read its IP.
"""
import re
import secrets
import string

PREFIX = "PIP-"
_ALPHABET = string.ascii_letters + string.digits
_RE = re.compile(r"^PIP-([A-Za-z0-9]{20,48})$")


def generate_license(length=24):
    if not 20 <= length <= 48:
        raise ValueError("length must be 20..48")
    return PREFIX + "".join(secrets.choice(_ALPHABET) for _ in range(length))


def is_valid(key):
    return isinstance(key, str) and bool(_RE.match(key.strip()))


def topics(key):
    """Return (command_topic, reply_topic) derived from a license."""
    m = _RE.match(key.strip()) if isinstance(key, str) else None
    if not m:
        raise ValueError("invalid license format (expected PIP-XXXXXXXXXXXXXXXXXXXXXXXX)")
    body = m.group(1)
    return f"pip-c-{body}", f"pip-r-{body}"
