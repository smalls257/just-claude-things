public static class Mw { public static IApplicationBuilder Use(this IApplicationBuilder a) { a.UseSerilogRequestLogging(); return a; } }
