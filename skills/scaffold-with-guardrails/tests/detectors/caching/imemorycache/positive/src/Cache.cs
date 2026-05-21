public static class CacheExt
{
    public static IServiceCollection AddMem(this IServiceCollection s)
    {
        s.AddMemoryCache();
        return s;
    }
}
