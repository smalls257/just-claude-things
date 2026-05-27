public class ApiResponse<T>
{
    public bool Success { get; init; }
    public T Data { get; init; }
}
