public static class CookieOnly
{
    public static IServiceCollection AddCookieOnly(this IServiceCollection s)
    {
        s.AddAuthentication().AddCookie();
        return s;
    }
}
