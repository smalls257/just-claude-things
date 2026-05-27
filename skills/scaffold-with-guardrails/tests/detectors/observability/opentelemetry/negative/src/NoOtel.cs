using Microsoft.Extensions.DependencyInjection;

public static class NoOtel
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        return s;
    }
}
