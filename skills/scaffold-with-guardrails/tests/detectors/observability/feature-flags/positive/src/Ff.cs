using Microsoft.Extensions.DependencyInjection;

public static class Ff
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddFeatureManagement();
        return s;
    }
}
