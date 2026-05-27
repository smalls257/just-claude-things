using Microsoft.AspNetCore.Builder;

public static class NoEx
{
    public static IApplicationBuilder X(this IApplicationBuilder a)
    {
        return a;
    }
}
