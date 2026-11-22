# GD OS PC agent

The server protocol is in place. A gaming PC is paired by MAC address and hardware id. On each heartbeat the server returns `LOCK` or `UNLOCK`. Unlock is returned only while that PC has an active session.

`simulator.py` sends one heartbeat from this Mac:

```bash
python3 agent/simulator.py --mac aa:bb:cc:dd:ee:01 --hardware 11111111-1111-4111-8111-111111111111
```

The simulator does not cover a Windows desktop.

`agent/windows` is the .NET 8 agent. It posts the same heartbeat. On Windows, `LOCK` shows a fullscreen cover in the player session and `UNLOCK` hides it. The agent does not call the Windows lock screen, because it cannot dismiss that screen when a session starts. A failed heartbeat, or an action other than `LOCK` or `UNLOCK`, keeps the cover up. On this Mac the same program only prints the action.

It needs the .NET 8 SDK. This machine's older `dotnet` on `PATH` is SDK 7, so use a .NET 8 install:

```bash
cd agent/windows
dotnet test
GD_OS_AGENT_MAC=aa:bb:cc:dd:ee:11 GD_OS_AGENT_HARDWARE=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa dotnet run --project GdOs.Agent -- --once
```

Publish a 64-bit Windows program from the Mac:

```bash
dotnet publish GdOs.Agent/GdOs.Agent.csproj -c Release -r win-x64 --self-contained -o /tmp/gdos-agent-win
```

Run `gdos-agent.exe` when the player signs in, not as a Windows service. A service in session 0 cannot cover the player desktop. Copying it into a CCBoot image, and checking the cover on one physical PC, is still to do.
