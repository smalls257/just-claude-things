using Microsoft.AspNetCore.Http;
using System.Threading.Tasks;

public class Plain
{
    public async Task X(HttpContext ctx, RequestDelegate next)
    {
        await next(ctx);
    }
}
