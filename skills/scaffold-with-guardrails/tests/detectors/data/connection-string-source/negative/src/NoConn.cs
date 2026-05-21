public static class NoConn { public static IServiceCollection X(this IServiceCollection s) { return s.AddSingleton<object>(); } }
