public static class Rl
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddRateLimiter(o => {});
        return s;
    }
}
