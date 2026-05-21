public static class Dp
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddDataProtection().PersistKeysToAzureBlobStorage("conn", "container", "key");
        return s;
    }
}
