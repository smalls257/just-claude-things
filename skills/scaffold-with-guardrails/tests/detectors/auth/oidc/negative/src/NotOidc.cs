public static class JwtOnly { public static IServiceCollection X(this IServiceCollection s) { s.AddJwtBearer(); return s; } }
