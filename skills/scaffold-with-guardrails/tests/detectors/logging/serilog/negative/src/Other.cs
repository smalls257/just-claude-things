public static class Other { public static void X(this IHostBuilder b) { b.ConfigureLogging(l => l.AddConsole()); } }
