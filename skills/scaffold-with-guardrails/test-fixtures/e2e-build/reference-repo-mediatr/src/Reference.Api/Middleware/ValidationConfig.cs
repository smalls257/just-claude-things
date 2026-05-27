using FluentValidation;
namespace Reference.Api.Middleware;

public static class ValidationConfig
{
    public static void AddValidation(this IServiceCollection services)
    {
        // Register all validators from this assembly — exercises AddValidatorsFromAssembly signal
        services.AddValidatorsFromAssembly(typeof(ValidationConfig).Assembly);
    }
}
