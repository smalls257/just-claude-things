using Microsoft.AspNetCore.Authentication.JwtBearer;
using Serilog;

var builder = WebApplication.CreateBuilder(args);
builder.Host.UseSerilog((ctx, cfg) => cfg.WriteTo.Console());
builder.Services.AddControllers();
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
                .AddJwtBearer(o => { o.Authority = "https://x"; });
var app = builder.Build();
app.UseSerilogRequestLogging();
app.UseAuthentication();
app.MapControllers();
app.Run();
