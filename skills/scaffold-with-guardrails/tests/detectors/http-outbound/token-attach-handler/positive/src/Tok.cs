using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

public class BearerTokenHandler : DelegatingHandler
{
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage r, CancellationToken c)
    {
        return base.SendAsync(r, c);
    }
}
