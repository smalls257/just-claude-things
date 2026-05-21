public static class OidcAuthExtensions
{
    public static IServiceCollection AddOidc(this IServiceCollection s)
    {
        s.AddAuthentication().AddOpenIdConnect(o => { o.Authority = "x"; });
        return s;
    }
}
