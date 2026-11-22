using System.Net.Http.Json;

namespace GdOs.Agent;

public sealed class HttpHeartbeatClient : IHeartbeatClient
{
    private readonly HttpClient _http;
    private readonly string _baseUrl;

    public HttpHeartbeatClient(HttpClient http, string baseUrl)
    {
        _http = http;
        _baseUrl = baseUrl.TrimEnd('/');
    }

    public async Task<AgentTick> SendAsync(string macAddress, string hardwareUuid, CancellationToken cancellationToken)
    {
        var body = new HeartbeatRequest(macAddress, hardwareUuid);
        using var response = await _http.PostAsJsonAsync($"{_baseUrl}/agent/heartbeat", body, cancellationToken);
        response.EnsureSuccessStatusCode();
        var parsed = await response.Content.ReadFromJsonAsync<HeartbeatResponse>(cancellationToken);
        if (parsed is null || string.IsNullOrWhiteSpace(parsed.station_code) || string.IsNullOrWhiteSpace(parsed.desired))
        {
            throw new InvalidOperationException("The server returned an empty heartbeat.");
        }
        return new AgentTick(parsed.station_code, parsed.desired);
    }

    private sealed record HeartbeatRequest(string mac_address, string hardware_uuid);

    private sealed class HeartbeatResponse
    {
        public string station_code { get; set; } = "";
        public string desired { get; set; } = "";
    }
}
