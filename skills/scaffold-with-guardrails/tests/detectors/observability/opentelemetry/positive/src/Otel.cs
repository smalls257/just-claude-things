using Microsoft.Extensions.DependencyInjection;
using OpenTelemetry.Trace;

public static class Otel
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddOpenTelemetry()
         .WithTracing(b => b.AddAspNetCoreInstrumentation());
        return s;
    }
}
