public static class Json
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.ConfigureHttpJsonOptions(o => o.SerializerOptions.WriteIndented = true);
        return s;
    }
}
