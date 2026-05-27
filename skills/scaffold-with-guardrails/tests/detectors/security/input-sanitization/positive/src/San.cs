public class San
{
    public string Clean(string x)
    {
        return HtmlEncoder.Default.Encode(x);
    }
}
