using System.Management;
using System.Net.NetworkInformation;

namespace GdOs.Agent;

public static class MachineIdentity
{
    public static (string Mac, string Hardware) Resolve(string? configuredMac, string? configuredHardware)
    {
        var mac = string.IsNullOrWhiteSpace(configuredMac) ? ReadMac() : configuredMac.Trim();
        var hardware = string.IsNullOrWhiteSpace(configuredHardware) ? ReadHardware() : configuredHardware.Trim();
        return (mac, hardware);
    }

    private static string ReadMac()
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new InvalidOperationException("This Mac run needs GD_OS_AGENT_MAC and GD_OS_AGENT_HARDWARE.");
        }
        foreach (var nic in NetworkInterface.GetAllNetworkInterfaces())
        {
            if (nic.OperationalStatus != OperationalStatus.Up || nic.NetworkInterfaceType == NetworkInterfaceType.Loopback)
            {
                continue;
            }
            var bytes = nic.GetPhysicalAddress().GetAddressBytes();
            if (bytes.Length != 6)
            {
                continue;
            }
            return string.Join(":", bytes.Select(part => part.ToString("x2")));
        }
        throw new InvalidOperationException("No network adapter was found.");
    }

    private static string ReadHardware()
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new InvalidOperationException("This Mac run needs GD_OS_AGENT_MAC and GD_OS_AGENT_HARDWARE.");
        }
        using var searcher = new ManagementObjectSearcher("SELECT UUID FROM Win32_ComputerSystemProduct");
        foreach (var item in searcher.Get())
        {
            var uuid = item["UUID"]?.ToString();
            if (!string.IsNullOrWhiteSpace(uuid))
            {
                return uuid;
            }
        }
        throw new InvalidOperationException("The hardware id was not found.");
    }
}
