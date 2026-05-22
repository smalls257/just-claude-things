using Microsoft.AspNetCore.Authentication.JwtBearer;
namespace Reference.Api.Auth;

public static class JwtAuthExtensions
{
    public static void AddJwtAuthentication(this WebApplicationBuilder builder)
    {
        builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
            .AddJwtBearer(options =>
            {
                options.Authority = builder.Configuration["Jwt:Authority"];
                options.Audience = builder.Configuration["Jwt:Audience"];
            });
    }
}
