public static class SerilogSetup
{
    public static IHostBuilder AddSerilog(this IHostBuilder b)
    { b.UseSerilog((ctx, cfg) => cfg.WriteTo.Console()); return b; }
}
