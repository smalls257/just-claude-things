public static class Med
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddMediatR(c => c.RegisterServicesFromAssembly(typeof(Med).Assembly));
        return s;
    }
}
