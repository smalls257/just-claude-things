using Microsoft.Extensions.DependencyInjection;

public static class NoHc
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        return s;
    }
}
