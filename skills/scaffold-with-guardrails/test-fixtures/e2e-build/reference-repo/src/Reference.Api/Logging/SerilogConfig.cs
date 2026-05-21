using Serilog;  // for structured logging — exercises inline-comment regex
namespace Reference.Api.Logging;

public static class SerilogConfig
{
    public static void Configure(WebApplicationBuilder builder)
    {
        Log.Logger = new LoggerConfiguration()
            .Enrich.FromLogContext()
            .WriteTo.Console()
            .CreateLogger();
        builder.Host.UseSerilog();
    }
}
