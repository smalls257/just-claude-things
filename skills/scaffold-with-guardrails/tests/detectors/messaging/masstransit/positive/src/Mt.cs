public static class Mt
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddMassTransit(b => b.UsingInMemory());
        return s;
    }
}
