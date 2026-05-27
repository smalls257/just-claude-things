public static class NoRedis
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddMemoryCache();
        return s;
    }
}
