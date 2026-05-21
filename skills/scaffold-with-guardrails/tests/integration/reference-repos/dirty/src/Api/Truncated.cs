public static class Bad
{
    public static IServiceCollection AddBad(this IServiceCollection s)
    {
        s.AddJwtBearer();
