from pathlib import Path
from convention_scan.discovery import sweep, DiscoveryCandidate


def write(p, body):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_finds_addX_extension_methods(tmp_path):
    write(tmp_path / "src" / "FlagsExtensions.cs", """
namespace App;
public static class FlagsExtensions
{
    public static IServiceCollection AddFlags(this IServiceCollection s)
    {
        // ten lines of body
        s.AddSingleton<IFlagSource, FlagSource>();
        return s;
    }
}
""")
    cands = sweep(tmp_path, claimed_files=set(), top_n=5)
    assert any(c.name == "flags" or "Flags" in c.source_path for c in cands)


def test_skips_claimed_files(tmp_path):
    cs_path = tmp_path / "src" / "AlreadyClaimed.cs"
    write(cs_path, """
public static class XExtensions
{
    public static IServiceCollection AddX(this IServiceCollection s) { return s; }
}
""")
    cands = sweep(tmp_path, claimed_files={str(cs_path)}, top_n=5)
    assert all(c.source_path != str(cs_path) for c in cands)


def test_top_n_cap_respected(tmp_path):
    for i in range(10):
        write(tmp_path / "src" / f"F{i}Extensions.cs", f"""
public static class F{i}Extensions
{{
    public static IServiceCollection AddF{i}(this IServiceCollection s) {{ return s; }}
}}
""")
    cands = sweep(tmp_path, claimed_files=set(), top_n=5)
    assert len(cands) == 5


def test_discover_all_returns_everything(tmp_path):
    for i in range(8):
        write(tmp_path / "src" / f"F{i}Extensions.cs", f"""
public static class F{i}Extensions
{{
    public static IServiceCollection AddF{i}(this IServiceCollection s) {{ return s; }}
}}
""")
    cands = sweep(tmp_path, claimed_files=set(), top_n=None)
    assert len(cands) == 8


def test_unsignaled_files_ignored(tmp_path):
    write(tmp_path / "src" / "Random.cs", "public class Random { public void Hi() {} }")
    cands = sweep(tmp_path, claimed_files=set(), top_n=5)
    assert cands == []
