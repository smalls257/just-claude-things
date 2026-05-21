using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.Extensions.DependencyInjection;
public static class JwtAuthExtensions
{
    public static IServiceCollection AddJwtAuth(this IServiceCollection s)
    {
        s.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
         .AddJwtBearer(o => { o.Authority = "https://example.com"; });
        return s;
    }
}
