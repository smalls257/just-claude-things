public static class TenancyExt
{
    public static IServiceCollection AddTenancy(this IServiceCollection s)
    { s.AddMultiTenant<AppTenantInfo>().WithRouteStrategy(); return s; }
}
