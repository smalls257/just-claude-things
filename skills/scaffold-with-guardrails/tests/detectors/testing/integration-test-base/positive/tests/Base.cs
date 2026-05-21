public abstract class IntegrationTestBase
{
    protected HttpClient Client;
    protected IntegrationTestBase() { Client = new HttpClient(); }
}
