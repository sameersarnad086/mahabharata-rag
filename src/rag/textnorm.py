"""Text normalisation used to compare evidence phrases with passage text."""
import re


def norm(s: str) -> str:
    """Lower-case, straighten curly quotes and dashes, collapse whitespace."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()
