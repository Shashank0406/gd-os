"""Mac simulator for the GD OS agent protocol.

This asks the server whether a paired PC should lock or unlock. It does not
lock a Windows desktop.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Send one GD OS agent heartbeat")
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--mac", required=True)
    parser.add_argument("--hardware", required=True)
    args = parser.parse_args()
    payload = json.dumps({"mac_address": args.mac, "hardware_uuid": args.hardware}).encode()
    request = urllib.request.Request(
        args.base.rstrip("/") + "/agent/heartbeat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        print(detail or exc.reason, file=sys.stderr)
        return 1
    print(f"{body['station_code']} {body['desired']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
