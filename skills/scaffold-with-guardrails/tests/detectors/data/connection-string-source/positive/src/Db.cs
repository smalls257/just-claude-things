public static class DbExt
{
    public static IServiceCollection AddDb(this IServiceCollection s, IConfiguration cfg)
    { return s.AddDbContext<AppCtx>(o => o.UseSqlServer(cfg.GetConnectionString("Default"))); }
}
