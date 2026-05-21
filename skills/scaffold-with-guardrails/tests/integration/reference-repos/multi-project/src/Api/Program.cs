using Microsoft.AspNetCore.Authentication.JwtBearer;
var b = WebApplication.CreateBuilder(args);
b.Services.AddAuthentication().AddJwtBearer(o => o.Authority = "x");
b.Build().Run();
