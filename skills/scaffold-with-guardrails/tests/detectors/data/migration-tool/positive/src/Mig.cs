public static class MigExt
{
    public static IServiceProvider RunMigrations(this IServiceProvider sp)
    { using var scope = sp.CreateScope(); var context = scope.ServiceProvider.GetRequiredService<AppCtx>(); context.Database.Migrate(); return sp; }
}
