using System.Runtime.InteropServices;

namespace GdOs.Agent;

internal sealed class WindowsSessionGuard : ISessionGuard
{
    private readonly Thread _thread;
    private readonly Native.WndProc _proc;
    private volatile bool _locked = true;

    public WindowsSessionGuard()
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("The desktop cover runs on Windows.");
        }
        _proc = WindowProc;
        _thread = new Thread(Run)
        {
            IsBackground = true,
            Name = "gdos-agent-cover",
        };
        _thread.SetApartmentState(ApartmentState.STA);
        _thread.Start();
    }

    public void Apply(string desired)
    {
        _locked = desired != "UNLOCK";
    }

    private void Run()
    {
        var instance = Native.GetModuleHandle(null);
        var klass = new Native.WNDCLASS
        {
            lpfnWndProc = _proc,
            hInstance = instance,
            hbrBackground = Native.CreateSolidBrush(0x00101812),
            lpszClassName = "GdOsAgentCover",
        };
        Native.RegisterClass(ref klass);
        var width = Native.GetSystemMetrics(0);
        var height = Native.GetSystemMetrics(1);
        var hwnd = Native.CreateWindowEx(
            Native.WS_EX_TOPMOST | Native.WS_EX_TOOLWINDOW,
            klass.lpszClassName,
            "Gamers District",
            Native.WS_POPUP | Native.WS_VISIBLE,
            0,
            0,
            width,
            height,
            IntPtr.Zero,
            IntPtr.Zero,
            instance,
            IntPtr.Zero);
        Native.SetWindowPos(hwnd, new IntPtr(-1), 0, 0, width, height, Native.SWP_SHOWWINDOW);
        Native.SetTimer(hwnd, new IntPtr(1), 200, IntPtr.Zero);
        while (Native.GetMessage(out var message, IntPtr.Zero, 0, 0) > 0)
        {
            Native.TranslateMessage(ref message);
            Native.DispatchMessage(ref message);
        }
    }

    private IntPtr WindowProc(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam)
    {
        if (message == Native.WM_CLOSE && _locked)
        {
            return IntPtr.Zero;
        }
        if (message == Native.WM_TIMER)
        {
            if (_locked)
            {
                Native.ShowWindow(hwnd, Native.SW_SHOW);
                Native.SetForegroundWindow(hwnd);
            }
            else
            {
                Native.ShowWindow(hwnd, Native.SW_HIDE);
            }
            return IntPtr.Zero;
        }
        return Native.DefWindowProc(hwnd, message, wParam, lParam);
    }

    private static class Native
    {
        public const int WS_POPUP = unchecked((int)0x80000000);
        public const int WS_VISIBLE = 0x10000000;
        public const int WS_EX_TOPMOST = 0x00000008;
        public const int WS_EX_TOOLWINDOW = 0x00000080;
        public const int SW_HIDE = 0;
        public const int SW_SHOW = 5;
        public const uint SWP_SHOWWINDOW = 0x0040;
        public const uint WM_CLOSE = 0x0010;
        public const uint WM_TIMER = 0x0113;

        public delegate IntPtr WndProc(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        public struct WNDCLASS
        {
            public uint style;
            public WndProc? lpfnWndProc;
            public int cbClsExtra;
            public int cbWndExtra;
            public IntPtr hInstance;
            public IntPtr hIcon;
            public IntPtr hCursor;
            public IntPtr hbrBackground;
            public string? lpszMenuName;
            public string lpszClassName;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct MSG
        {
            public IntPtr hwnd;
            public uint message;
            public IntPtr wParam;
            public IntPtr lParam;
            public uint time;
            public int ptX;
            public int ptY;
        }

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        public static extern ushort RegisterClass(ref WNDCLASS lpWndClass);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        public static extern IntPtr CreateWindowEx(
            int dwExStyle,
            string lpClassName,
            string lpWindowName,
            int dwStyle,
            int x,
            int y,
            int nWidth,
            int nHeight,
            IntPtr hWndParent,
            IntPtr hMenu,
            IntPtr hInstance,
            IntPtr lpParam);

        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int x, int y, int cx, int cy, uint uFlags);

        [DllImport("user32.dll")]
        public static extern int GetSystemMetrics(int nIndex);

        [DllImport("user32.dll")]
        public static extern IntPtr SetTimer(IntPtr hWnd, IntPtr nIDEvent, uint uElapse, IntPtr lpTimerFunc);

        [DllImport("user32.dll")]
        public static extern int GetMessage(out MSG lpMsg, IntPtr hWnd, uint wMsgFilterMin, uint wMsgFilterMax);

        [DllImport("user32.dll")]
        public static extern bool TranslateMessage(ref MSG lpMsg);

        [DllImport("user32.dll")]
        public static extern IntPtr DispatchMessage(ref MSG lpMsg);

        [DllImport("user32.dll")]
        public static extern IntPtr DefWindowProc(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

        [DllImport("gdi32.dll")]
        public static extern IntPtr CreateSolidBrush(uint color);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
        public static extern IntPtr GetModuleHandle(string? lpModuleName);
    }
}
