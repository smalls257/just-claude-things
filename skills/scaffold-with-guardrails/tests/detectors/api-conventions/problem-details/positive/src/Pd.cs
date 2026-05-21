public static class Pd
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddProblemDetails();
        return s;
    }
}
