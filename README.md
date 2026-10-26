# phoneip

Rotate your phone's mobile IP from Python or the command line.

## Install
```
pip install .            # from this folder
pip install ".[discord]" # with discord.py for the example bot
```

## Android (ADB)
Enable USB debugging, install `adb`, connect the phone.
```python
from phoneip import AdbRotator
r = AdbRotator()            # AdbRotator(serial="XXXX", method="airplane", root=True)
print(r.rotate())           # new IP
```
CLI: `phoneip rotate` / `phoneip ip`

## iPhone / other (webhook)
Create a Shortcut (airplane on -> wait 3s -> off) and trigger it via Pushcut/ntfy URL.
```python
from phoneip import HttpHookRotator
r = HttpHookRotator("https://api.pushcut.io/<key>/notifications/rotate")
print(r.rotate())
```
CLI: `phoneip rotate --mode hook --url <URL>`

## License mode (recommended): phone <-> your own Discord bot
The phone makes a **license** (`PIP-...`). Paste it into your bot; both sides derive the same private
ntfy topics from it. No ADB, no open ports, no server of your own. Setup: `docs/PHONE_SETUP.md`

- Android: in Termux run `phoneip agent` -> prints the license, then listens for commands.
- iPhone: Shortcut `RotateIP` (shows the license on first run) + Pushcut Automation Server (Pro).

In your bot (see `examples/bot_snippet.py`):
```python
from phoneip import rotate_with_license
ip = await rotate_with_license(license, trigger_url=None)   # iPhone: Pushcut URL as trigger_url
```
Manual / old style: `RemoteRotator(trigger_url, reply_topic)`; CLI: `phoneip rotate --mode remote --license PIP-...`

## Notes
- Check IP from the PC works when the PC is tethered through the phone; otherwise use `ip_source="device"` (Android).
- Some carriers (CGNAT) may return the same IP; `rotate()` retries then raises `RotateError`.
- Use only on devices you own or have consent for, and respect the terms of services you access.
