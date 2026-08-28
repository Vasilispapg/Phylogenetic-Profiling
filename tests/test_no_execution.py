"""
Uploaded content is data, never instructions.

Everything a user sends is handed to pandas, numpy, scipy or Bio.Phylo to be
parsed. Nothing shells out, deserialises Python objects, or evaluates a string.
This test fails if that ever stops being true, which is easier to notice here
than in review.
"""
import pathlib
import re

import pytest

ROOTS = ["app.py", "jobs.py", "guard.py", "workers.py", "config.py", "main.py",
         "analysis", "blueprints", "tree_construction", "visualization"]

# Each of these turns data into behaviour, one way or another.
FORBIDDEN = {
    r"\beval\s*\(": "eval() executes a string",
    r"\bexec\s*\(": "exec() executes a string",
    # re.compile is fine; the builtin is not.
    r"(?<!re\.)(?<!\w)compile\s*\(": "compile() turns a string into code",
    r"\b__import__\s*\(": "__import__() imports a named module at runtime",
    r"\bpickle\s*\.\s*loads?\b": "pickle deserialises arbitrary objects",
    r"\bmarshal\s*\.\s*loads?\b": "marshal deserialises code objects",
    r"\byaml\s*\.\s*load\s*\(": "yaml.load without SafeLoader constructs objects",
    r"\bos\s*\.\s*(system|popen|exec[lv])": "os process execution",
    r"\bsubprocess\s*\.": "subprocess runs a program",
    r"shell\s*=\s*True": "a shell interprets the command string",
}


def sources():
    for root in ROOTS:
        path = pathlib.Path(root)
        if path.is_file():
            yield path
        else:
            yield from sorted(p for p in path.rglob("*.py") if "__pycache__" not in p.parts)


def code_lines(path):
    """Lines with comments and docstring bodies stripped, so prose does not trip it."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'"""[\s\S]*?"""', '""', text)
    text = re.sub(r"'''[\s\S]*?'''", "''", text)
    for number, line in enumerate(text.splitlines(), 1):
        code = line.split("#", 1)[0]
        if code.strip():
            yield number, code


@pytest.mark.parametrize("path", list(sources()), ids=lambda p: str(p))
def test_no_execution_primitives(path):
    hits = [
        f"{path}:{number}: {why} → {code.strip()[:80]}"
        for number, code in code_lines(path)
        for pattern, why in FORBIDDEN.items()
        if re.search(pattern, code)
    ]
    assert not hits, "code execution reachable from user input:\n" + "\n".join(hits)


def test_json_is_parsed_not_evaluated():
    """Feature-matrix cells are JSON objects; they are loaded, never evaluated."""
    from analysis.matrix_io import _parse_cell
    assert _parse_cell('{"a": 1}') == {"a": 1}
    assert _parse_cell("__import__('os').system('true')") == {}
    assert _parse_cell("{'a': 1}") == {}          # not valid JSON, so not accepted
