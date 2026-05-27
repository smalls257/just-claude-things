public class WafTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> _f;
    public WafTests(WebApplicationFactory<Program> f) { _f = f; }
}
