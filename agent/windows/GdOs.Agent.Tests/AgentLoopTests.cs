using System.Net;
using System.Net.Sockets;
using System.Text;
using GdOs.Agent;
using Xunit;

namespace GdOs.Agent.Tests;

public sealed class AgentLoopTests
{
    [Fact]
    public async Task Unlock_is_applied_only_when_the_server_says_so()
    {
        var guard = new RecordingGuard();
        var loop = new AgentLoop(new FakeHeartbeat("PC-01", "UNLOCK"), guard);

        var tick = await loop.TickAsync("aa:bb:cc:dd:ee:11", "hardware", CancellationToken.None);

        Assert.Equal("PC-01", tick.StationCode);
        Assert.Equal("UNLOCK", tick.Desired);
        Assert.Equal(new[] { "UNLOCK" }, guard.Actions);
    }

    [Fact]
    public async Task A_failed_heartbeat_covers_the_desktop()
    {
        var guard = new RecordingGuard();
        var loop = new AgentLoop(new BrokenHeartbeat(), guard);

        await Assert.ThrowsAsync<HttpRequestException>(() => loop.TickAsync("aa", "hardware", CancellationToken.None));

        Assert.Equal(new[] { "LOCK" }, guard.Actions);
    }

    [Fact]
    public async Task An_unknown_action_covers_the_desktop()
    {
        var guard = new RecordingGuard();
        var loop = new AgentLoop(new FakeHeartbeat("PC-01", "OPEN"), guard);

        var error = await Assert.ThrowsAsync<InvalidOperationException>(() => loop.TickAsync("aa", "hardware", CancellationToken.None));

        Assert.Equal("The server returned an unknown action.", error.Message);
        Assert.Equal(new[] { "LOCK" }, guard.Actions);
    }

    [Fact]
    public void A_mac_run_uses_the_configured_identity()
    {
        var (mac, hardware) = MachineIdentity.Resolve("AA:BB:CC:DD:EE:11", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");

        Assert.Equal("AA:BB:CC:DD:EE:11", mac);
        Assert.Equal("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", hardware);
        Assert.Throws<InvalidOperationException>(() => MachineIdentity.Resolve(null, null));
    }

    [Fact]
    public async Task The_client_posts_the_paired_ids_and_reads_the_action()
    {
        var port = FreePort();
        using var listener = new HttpListener();
        listener.Prefixes.Add($"http://127.0.0.1:{port}/");
        listener.Start();
        var seen = new TaskCompletionSource<string>();
        var serve = Task.Run(async () =>
        {
            var context = await listener.GetContextAsync();
            using var reader = new StreamReader(context.Request.InputStream);
            seen.TrySetResult(await reader.ReadToEndAsync());
            var json = Encoding.UTF8.GetBytes("{\"station_code\":\"PC-01\",\"desired\":\"LOCK\",\"session_id\":null,\"server_time_utc\":\"2026-11-22T18:30:00+00:00\"}");
            context.Response.StatusCode = 200;
            context.Response.ContentType = "application/json";
            await context.Response.OutputStream.WriteAsync(json);
            context.Response.Close();
        });
        try
        {
            using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };
            var client = new HttpHeartbeatClient(http, $"http://127.0.0.1:{port}");
            var tick = await client.SendAsync("aa:bb:cc:dd:ee:11", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", CancellationToken.None);
            var body = await seen.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await serve;

            Assert.Equal("PC-01", tick.StationCode);
            Assert.Equal("LOCK", tick.Desired);
            Assert.Contains("aa:bb:cc:dd:ee:11", body);
            Assert.Contains("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", body);
        }
        finally
        {
            listener.Stop();
        }
    }

    private static int FreePort()
    {
        var tcp = new TcpListener(IPAddress.Loopback, 0);
        tcp.Start();
        var port = ((IPEndPoint)tcp.LocalEndpoint).Port;
        tcp.Stop();
        return port;
    }

    private sealed class RecordingGuard : ISessionGuard
    {
        public List<string> Actions { get; } = new();

        public void Apply(string desired)
        {
            Actions.Add(desired);
        }
    }

    private sealed class FakeHeartbeat : IHeartbeatClient
    {
        private readonly string _station;
        private readonly string _desired;

        public FakeHeartbeat(string station, string desired)
        {
            _station = station;
            _desired = desired;
        }

        public Task<AgentTick> SendAsync(string macAddress, string hardwareUuid, CancellationToken cancellationToken)
        {
            return Task.FromResult(new AgentTick(_station, _desired));
        }
    }

    private sealed class BrokenHeartbeat : IHeartbeatClient
    {
        public Task<AgentTick> SendAsync(string macAddress, string hardwareUuid, CancellationToken cancellationToken)
        {
            throw new HttpRequestException("The server did not answer.");
        }
    }
}
