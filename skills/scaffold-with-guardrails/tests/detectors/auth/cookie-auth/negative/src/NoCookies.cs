public static class NoCookies
{
    public static IServiceCollection AddJwt(this IServiceCollection s)
    { s.AddJwtBearer(); return s; }
}
