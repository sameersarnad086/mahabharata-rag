"""Edge-case checks for fixed_size_spans. Run: python tests/test_chunking.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag.chunking import fixed_size_spans


def check(name, got, want):
    ok = got == want
    print(("PASS" if ok else "FAIL"), name, "" if ok else f"\n   got  {got}\n   want {want}")
    return ok


def raises(name, fn):
    try:
        fn()
    except ValueError:
        print("PASS", name); return True
    except Exception as e:
        print("FAIL", name, f"raised {type(e).__name__}"); return False
    print("FAIL", name, "did not raise"); return False


results = [
    check("empty text", fixed_size_spans("", 10, 2), []),
    check("shorter than size -> one chunk", fixed_size_spans("a" * 5, 10, 2), [(0, 5)]),
    check("exact size -> one chunk", fixed_size_spans("a" * 10, 10, 2), [(0, 10)]),
    check("step = size - overlap", fixed_size_spans("a" * 18, 10, 2), [(0, 10), (8, 18)]),
    check("last chunk is shorter", fixed_size_spans("a" * 20, 10, 2), [(0, 10), (8, 18), (16, 20)]),
    check("no overlap", fixed_size_spans("a" * 25, 10, 0), [(0, 10), (10, 20), (20, 25)]),
    raises("overlap == size", lambda: fixed_size_spans("a" * 20, 10, 10)),
    raises("overlap > size", lambda: fixed_size_spans("a" * 20, 10, 12)),
]
# invariant: every character is covered by at least one chunk
spans = fixed_size_spans("a" * 1234, 100, 20)
covered = set()
for s, e in spans:
    covered.update(range(s, e))
results.append(check("full coverage", len(covered), 1234))
print(f"\n{sum(results)}/{len(results)} passed")
