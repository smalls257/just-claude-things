public static class Sw
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddSwaggerGen(o => { o.SwaggerDoc("v1", new() { Title = "api" }); });
        return s;
    }
}
