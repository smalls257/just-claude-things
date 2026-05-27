using Microsoft.Extensions.DependencyInjection;

public static class Ai
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddApplicationInsightsTelemetry();
        return s;
    }
}
