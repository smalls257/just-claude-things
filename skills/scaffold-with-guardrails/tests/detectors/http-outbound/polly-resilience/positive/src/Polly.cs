using Microsoft.Extensions.DependencyInjection;
using Polly;
using System.Net.Http;

public interface IClient { }

public class Client : IClient { }

public static class PollyExt
{
    public static IServiceCollection X(this IServiceCollection s)
    {
        s.AddHttpClient<IClient, Client>()
         .AddPolicyHandler(Policy.NoOpAsync<HttpResponseMessage>());
        return s;
    }
}
