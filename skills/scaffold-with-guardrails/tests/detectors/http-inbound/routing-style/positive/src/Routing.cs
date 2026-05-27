public static class Routing
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddControllers();
        return s;
    }
}
