using Microsoft.Extensions.DependencyInjection;
public static class FlagsExtensions
{
    public static IServiceCollection AddFlags(this IServiceCollection s)
    {
        s.AddSingleton<IFlagProvider, FlagProvider>();
        return s;
    }
}
