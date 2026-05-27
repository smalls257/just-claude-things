public static class Out
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddMassTransit(b => { b.AddEntityFrameworkOutbox<AppCtx>(o => {}); });
        return s;
    }
}
