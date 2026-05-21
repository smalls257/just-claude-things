public static class AuthZExt
{
    public static IServiceCollection AddAuthZ(this IServiceCollection s)
    {
        s.AddAuthorization(options =>
        {
            options.AddPolicy("admin", p => p.RequireRole("admin"));
        });
        return s;
    }
}
