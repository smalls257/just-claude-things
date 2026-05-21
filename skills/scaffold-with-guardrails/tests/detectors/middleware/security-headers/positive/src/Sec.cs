using Microsoft.AspNetCore.Builder;

public static class Sec
{
    public static IApplicationBuilder X(this IApplicationBuilder a)
    {
        return a.UseSecurityHeaders();
    }
}
