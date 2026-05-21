public static class Sec
{
    public static IConfigurationBuilder X(this IConfigurationBuilder c)
    {
        c.AddAzureKeyVault(new Uri("https://x"), new DefaultAzureCredential());
        return c;
    }
}
