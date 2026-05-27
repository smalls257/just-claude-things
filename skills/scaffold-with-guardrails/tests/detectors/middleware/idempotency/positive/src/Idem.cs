using Microsoft.AspNetCore.Http;
using System.Threading.Tasks;

public class IdempotencyMiddleware
{
    public async Task Invoke(HttpContext ctx, RequestDelegate next)
    {
        var key = ctx.Request.Headers["Idempotency-Key"];
        await next(ctx);
    }
}
