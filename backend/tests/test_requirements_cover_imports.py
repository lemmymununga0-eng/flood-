"""Production installs ONLY requirements.txt. Every third-party package the app imports must be
listed there, or the deployed container crashes at import time (as happened with httpx)."""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
# import name -> distribution name, where they differ
ALIAS = {"jose": "python-jose", "sklearn": "scikit-learn", "dotenv": "python-dotenv",
         "psycopg2": "psycopg2-binary", "multipart": "python-multipart", "starlette": "fastapi"}


def _imports(folder: str) -> set[str]:
    found: set[str] = set()
    for f in (ROOT / folder).rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return found - set(sys.stdlib_module_names) - {"app"}


def test_every_runtime_import_is_in_requirements_txt():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    listed = {n.replace("_", "-") for n in re.findall(r"^([a-z0-9_.\-]+)==", text, re.M)}
    missing = sorted(
        m for m in _imports("app") | _imports("alembic")
        if ALIAS.get(m, m).lower().replace("_", "-") not in listed
    )
    assert not missing, f"imported by the app but absent from requirements.txt: {missing}"
