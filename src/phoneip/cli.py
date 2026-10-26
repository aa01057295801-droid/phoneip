import argparse
from . import AdbRotator, HttpHookRotator, RemoteRotator, RotateError
from .license import generate_license, is_valid, topics


def main():
    p = argparse.ArgumentParser(prog="phoneip", description="Rotate phone mobile IP")
    p.add_argument("action", choices=["ip", "rotate", "license", "agent"])
    p.add_argument("--mode", choices=["adb", "hook", "remote"], default="adb")
    p.add_argument("--serial", help="adb device serial")
    p.add_argument("--method", choices=["data", "airplane"], default=None,
                   help="adb default: data; agent default: airplane (falls back to data)")
    p.add_argument("--root", action="store_true")
    p.add_argument("--ip-source", choices=["host", "device"], default="host")
    p.add_argument("--url", help="trigger URL (hook mode; remote mode with iPhone/Pushcut)")
    p.add_argument("--reply-topic", help="ntfy topic the phone replies its IP to (remote mode)")
    p.add_argument("--license", help="license shown by the phone (remote mode / agent)")
    p.add_argument("--backend", choices=["auto", "root", "adb", "local"], default="auto",
                   help="agent: how to get permission to toggle airplane mode")
    p.add_argument("--keep-wifi", action="store_true", help="agent: do not turn Wi-Fi off")
    p.add_argument("--retries", type=int, default=3)
    a = p.parse_args()

    if a.action == "license":
        key = generate_license()
        cmd, reply = topics(key)
        print(f"license: {key}\ncommand topic: {cmd}\nreply topic: {reply}")
        return

    if a.action == "agent":
        from .agent import AndroidAgent, load_or_create_license
        key = a.license or load_or_create_license()
        print("=" * 40, f"\nLICENSE: {key}\n" + "=" * 40, flush=True)
        AndroidAgent(key, backend=a.backend, keep_wifi=a.keep_wifi,
                     method=a.method or "airplane").run_forever()
        return

    if a.mode == "remote":
        if a.license:
            if not is_valid(a.license):
                p.error("invalid --license")
            r = RemoteRotator.from_license(a.license, trigger_url=a.url)
        elif a.url and a.reply_topic:
            r = RemoteRotator(a.url, a.reply_topic)
        else:
            p.error("remote mode needs --license, or --url and --reply-topic")
    elif a.mode == "hook":
        if not a.url:
            p.error("--url is required in hook mode")
        r = HttpHookRotator(a.url)
    else:
        r = AdbRotator(a.serial, a.method or "data", a.root, a.ip_source)

    if a.action == "ip":
        print(r.get_ip())
    else:
        try:
            print(r.rotate(a.retries))
        except RotateError as e:
            raise SystemExit(str(e))


if __name__ == "__main__":
    main()
