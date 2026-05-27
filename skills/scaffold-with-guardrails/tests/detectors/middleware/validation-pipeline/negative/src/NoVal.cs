using Microsoft.Extensions.DependencyInjection;

public static class NoVal
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        return s;
    }
}
