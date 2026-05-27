var builder = WebApplication.CreateBuilder(args);

// {{CONVENTION:logging}}

var app = builder.Build();

// {{CONVENTION:middleware}}

app.Run();
