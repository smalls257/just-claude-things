var builder = WebApplication.CreateBuilder(args);

// {{CONVENTION:logging}}
// {{CONVENTION:observability}}
// {{CONVENTION:auth}}
// {{CONVENTION:data}}
// {{CONVENTION:http-outbound}}

var app = builder.Build();

// {{CONVENTION:middleware}}

app.Run();
