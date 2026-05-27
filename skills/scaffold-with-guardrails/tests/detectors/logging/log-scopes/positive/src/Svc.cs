public class Svc
{
    public void Run(ILogger<Svc> log) { using (log.BeginScope("op")) { log.LogInformation("hi"); } }
}
