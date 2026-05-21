public static class Cors
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddCors(o => o.AddPolicy("p", b => b.AllowAnyOrigin()));
        return s;
    }
}
