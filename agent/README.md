# GD OS PC agent

The server protocol is in place. A gaming PC is paired by MAC address and hardware id. On each heartbeat the server returns `LOCK` or `UNLOCK`. Unlock is returned only while that PC has an active session.

`simulator.py` sends one heartbeat from this Mac:

```bash
python3 agent/simulator.py --mac aa:bb:cc:dd:ee:01 --hardware 11111111-1111-4111-8111-111111111111
```

The simulator does not lock a Windows desktop. The C# Windows service is not created yet. Lock and unlock stay unverified until one physical diskless PC test is recorded in TESTING.md.
