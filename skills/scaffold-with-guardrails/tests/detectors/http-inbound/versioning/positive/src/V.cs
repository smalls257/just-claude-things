public static class V
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddApiVersioning();
        return s;
    }
}
