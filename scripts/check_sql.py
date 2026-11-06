"""Offline syntax check with the PostgreSQL parser (pip install pglast).
This does not replace a real PostGIS integration test.
"""

import ast
import re
from pathlib import Path
from pglast import parse_sql

namespace = {}
trees = []
for path in [
    *Path("backend/app/api").glob("*.py"),
    *Path("pipeline").glob("*.py"),
    Path("backend/migrations/versions/0004_brazil_science.py"),
]:
    trees.append((path, ast.parse(path.read_text(encoding="utf-8-sig"))))


def evaluate(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return namespace[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return evaluate(node.left) + evaluate(node.right)
    raise ValueError()


for _ in range(3):
    for path, tree in trees:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                try:
                    value = evaluate(node.value)
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            namespace[target.id] = value
                except (ValueError, KeyError):
                    pass
checked = 0
for path, tree in trees:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else getattr(node.func, "attr", "")
        )
        if name not in ("text", "query", "execute"):
            continue
        try:
            sql = evaluate(node.args[0])
        except (ValueError, KeyError):
            continue
        if not re.match(
            r"\s*(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b", sql, re.I
        ):
            continue
        sql = re.sub(r"(?<!:):[a-zA-Z_]\w*", "NULL", sql)
        try:
            parse_sql(sql)
        except Exception as exc:
            raise RuntimeError(f"{path}:{node.lineno}: {exc}\n{sql}") from exc
        checked += 1
print(f"{checked} PostgreSQL statements parsed successfully (offline).")
