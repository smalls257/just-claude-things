using Microsoft.AspNetCore.Http;
using System;
using System.Threading.Tasks;

public class CorrelationMiddleware
{
    private readonly RequestDelegate _next;

    public CorrelationMiddleware(RequestDelegate n)
    {
        _next = n;
    }

    public async Task Invoke(HttpContext ctx)
    {
        ctx.Response.Headers["X-Correlation-ID"] = Guid.NewGuid().ToString();
        await _next(ctx);
    }
}
