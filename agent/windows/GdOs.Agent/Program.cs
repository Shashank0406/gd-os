using GdOs.Agent;

var once = args.Contains("--once");
var intervalSeconds = 5;
if (int.TryParse(Environment.GetEnvironmentVariable("GD_OS_AGENT_INTERVAL_SECONDS"), out var configured) && configured >= 1)
{
    intervalSeconds = configured;
}
var baseUrl = Environment.GetEnvironmentVariable("GD_OS_AGENT_BASE") ?? "http://127.0.0.1:8000";
var (mac, hardware) = MachineIdentity.Resolve(
    Environment.GetEnvironmentVariable("GD_OS_AGENT_MAC"),
    Environment.GetEnvironmentVariable("GD_OS_AGENT_HARDWARE"));

using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };
var loop = new AgentLoop(new HttpHeartbeatClient(http, baseUrl), Guard());
if (once)
{
    try
    {
        var tick = await loop.TickAsync(mac, hardware, CancellationToken.None);
        Console.WriteLine($"{tick.StationCode} {tick.Desired}");
        return 0;
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine(ex.Message);
        return 1;
    }
}

using var stopping = new CancellationTokenSource();
Console.CancelKeyPress += (_, eventArgs) =>
{
    eventArgs.Cancel = true;
    stopping.Cancel();
};
while (!stopping.IsCancellationRequested)
{
    try
    {
        var tick = await loop.TickAsync(mac, hardware, stopping.Token);
        Console.WriteLine($"{tick.StationCode} {tick.Desired}");
    }
    catch (OperationCanceledException)
    {
        break;
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine(ex.Message);
    }
    try
    {
        await Task.Delay(TimeSpan.FromSeconds(intervalSeconds), stopping.Token);
    }
    catch (OperationCanceledException)
    {
        break;
    }
}
return 0;

static ISessionGuard Guard()
{
    return OperatingSystem.IsWindows() ? new WindowsSessionGuard() : new ConsoleGuard();
}
