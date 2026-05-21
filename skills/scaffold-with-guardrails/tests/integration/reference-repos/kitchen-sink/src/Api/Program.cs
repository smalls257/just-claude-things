using Microsoft.AspNetCore.Authentication.JwtBearer;
using Serilog;

var builder = WebApplication.CreateBuilder(args);
builder.Host.UseSerilog((ctx, c) => c.WriteTo.Console());
builder.Services.AddControllers();
builder.Services.AddAuthentication().AddJwtBearer(o => { o.Authority = "x"; });
builder.Services.AddStackExchangeRedisCache(o => o.Configuration = "x");
builder.Services.AddOpenTelemetry().WithTracing(b => b.AddAspNetCoreInstrumentation());
builder.Services.AddHealthChecks();
builder.Services.AddProblemDetails();
var app = builder.Build();
app.UseSerilogRequestLogging();
app.UseExceptionHandler("/error");
app.MapHealthChecks("/healthz");
app.Run();
