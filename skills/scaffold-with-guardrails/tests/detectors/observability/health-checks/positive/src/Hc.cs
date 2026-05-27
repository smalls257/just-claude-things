using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Diagnostics.HealthChecks;

public static class Hc
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddHealthChecks()
         .AddCheck("self", () => HealthCheckResult.Healthy());
        return s;
    }
}
