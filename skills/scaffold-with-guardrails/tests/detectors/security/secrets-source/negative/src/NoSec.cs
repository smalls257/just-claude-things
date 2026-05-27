public static class NoSec
{
    public static IConfigurationBuilder X(this IConfigurationBuilder c)
    {
        c.AddJsonFile("a.json");
        return c;
    }
}
