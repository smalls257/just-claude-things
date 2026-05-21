using Microsoft.Extensions.DependencyInjection;
using System.Net.Http;

public static class NoHttp
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        return s.AddSingleton<HttpClient>();
    }
}
