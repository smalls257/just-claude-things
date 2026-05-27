public static class RedisExt
{
    public static IServiceCollection AddRedis(this IServiceCollection s)
    {
        s.AddStackExchangeRedisCache(o => { o.Configuration = "x"; });
        return s;
    }
}
