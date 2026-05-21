using Microsoft.Extensions.DependencyInjection;

public interface IMyClient { }

public class MyClient : IMyClient { }

public static class HttpExt
{
    public static IServiceCollection AddSvc(this IServiceCollection s)
    {
        s.AddHttpClient<IMyClient, MyClient>();
        return s;
    }
}
