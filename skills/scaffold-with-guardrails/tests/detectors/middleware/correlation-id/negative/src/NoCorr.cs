using Microsoft.AspNetCore.Http;
using System.Threading.Tasks;

public class PlainMiddleware
{
    public async Task Invoke(HttpContext ctx, RequestDelegate next)
    {
        await next(ctx);
    }
}
