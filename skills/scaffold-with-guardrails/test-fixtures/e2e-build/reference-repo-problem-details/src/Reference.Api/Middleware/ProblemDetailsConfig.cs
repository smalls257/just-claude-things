using Microsoft.AspNetCore.Diagnostics;
namespace Reference.Api.Middleware;

public static class ProblemDetailsConfig
{
    public static void AddProblemDetailsHandling(this IServiceCollection services)
    {
        services.AddProblemDetails();
    }

    public static void UseProblemDetailsHandling(this WebApplication app)
    {
        // Wire RFC 7807 exception shaping for all unhandled exceptions.
        app.UseExceptionHandler(opts => opts.Run(async ctx =>
        {
            var feature = ctx.Features.Get<IExceptionHandlerFeature>();
            ctx.Response.StatusCode = StatusCodes.Status500InternalServerError;
            await ctx.Response.WriteAsJsonAsync(
                new { error = feature?.Error.Message ?? "unexpected error" });
        }));
    }
}
