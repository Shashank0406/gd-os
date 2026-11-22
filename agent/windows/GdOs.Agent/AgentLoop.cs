namespace GdOs.Agent;

public sealed record AgentTick(string StationCode, string Desired);

public interface IHeartbeatClient
{
    Task<AgentTick> SendAsync(string macAddress, string hardwareUuid, CancellationToken cancellationToken);
}

public interface ISessionGuard
{
    void Apply(string desired);
}

public sealed class AgentLoop
{
    private readonly IHeartbeatClient _client;
    private readonly ISessionGuard _guard;

    public AgentLoop(IHeartbeatClient client, ISessionGuard guard)
    {
        _client = client;
        _guard = guard;
    }

    public async Task<AgentTick> TickAsync(string macAddress, string hardwareUuid, CancellationToken cancellationToken)
    {
        try
        {
            var tick = await _client.SendAsync(macAddress, hardwareUuid, cancellationToken);
            var desired = RequireKnown(tick.Desired);
            _guard.Apply(desired);
            return tick with { Desired = desired };
        }
        catch (Exception) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            _guard.Apply("LOCK");
            throw;
        }
    }

    public static string RequireKnown(string desired)
    {
        if (desired is "LOCK" or "UNLOCK")
        {
            return desired;
        }
        throw new InvalidOperationException("The server returned an unknown action.");
    }
}
