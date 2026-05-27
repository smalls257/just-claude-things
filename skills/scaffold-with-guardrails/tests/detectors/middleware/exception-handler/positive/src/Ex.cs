using Microsoft.AspNetCore.Builder;

public static class Ex
{
    public static IApplicationBuilder X(this IApplicationBuilder a)
    {
        a.UseExceptionHandler("/error");
        return a;
    }
}
