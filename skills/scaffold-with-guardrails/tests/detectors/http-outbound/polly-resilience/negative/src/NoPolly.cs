using Microsoft.Extensions.DependencyInjection;

public interface IClient { }

public class Client : IClient { }

public static class NoPolly
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddHttpClient<IClient, Client>();
        return s;
    }
}
