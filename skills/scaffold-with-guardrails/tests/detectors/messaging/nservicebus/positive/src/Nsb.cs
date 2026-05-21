public static class Nsb
{
    public static IHostBuilder X(this IHostBuilder h)
    {
        return h.UseNServiceBus(_ => new EndpointConfiguration("svc"));
    }
}
