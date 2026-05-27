using Microsoft.Extensions.DependencyInjection;

public static class Val
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddValidatorsFromAssembly(typeof(Val).Assembly);
        return s;
    }
}
