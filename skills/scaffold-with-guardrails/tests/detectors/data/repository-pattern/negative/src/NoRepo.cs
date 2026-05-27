public static class NoRepo { public static IServiceCollection X(this IServiceCollection s) { return s.AddScoped<MyService>(); } }
