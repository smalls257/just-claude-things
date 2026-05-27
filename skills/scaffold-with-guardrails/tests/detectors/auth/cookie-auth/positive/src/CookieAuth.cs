public static class CookieExt
{
    public static IServiceCollection AddCookieAuth(this IServiceCollection s)
    { s.AddAuthentication().AddCookie(o => { o.LoginPath = "/login"; }); return s; }
}
