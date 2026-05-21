public static class RepoExt
{
    public static IServiceCollection AddRepos(this IServiceCollection s)
    { s.AddScoped<IUserRepository, UserRepository>(); s.AddScoped<IUnitOfWork, UnitOfWork>(); return s; }
}
