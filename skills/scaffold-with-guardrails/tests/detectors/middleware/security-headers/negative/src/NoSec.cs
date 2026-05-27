using Microsoft.AspNetCore.Builder;

public static class NoSec
{
    public static IApplicationBuilder X(this IApplicationBuilder a)
    {
        return a.UseRouting();
    }
}
