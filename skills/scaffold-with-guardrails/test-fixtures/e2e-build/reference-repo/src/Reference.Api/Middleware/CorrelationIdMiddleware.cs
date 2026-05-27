namespace Reference.Api.Middleware;

public sealed class CorrelationIdMiddleware
{
    private readonly RequestDelegate _next;
    private const string Header = "X-Correlation-ID";
    public CorrelationIdMiddleware(RequestDelegate next) => _next = next;
    public async Task InvokeAsync(HttpContext ctx)
    {
        if (!ctx.Request.Headers.ContainsKey(Header))
            ctx.Request.Headers[Header] = Guid.NewGuid().ToString();
        await _next(ctx);
    }
}
