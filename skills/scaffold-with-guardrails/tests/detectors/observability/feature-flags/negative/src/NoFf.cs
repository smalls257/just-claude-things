using Microsoft.Extensions.DependencyInjection;

public static class NoFf
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        return s;
    }
}
