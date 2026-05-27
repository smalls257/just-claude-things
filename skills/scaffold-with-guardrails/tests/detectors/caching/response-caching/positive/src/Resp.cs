public static class RespExt
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddResponseCaching();
        return s;
    }
}
