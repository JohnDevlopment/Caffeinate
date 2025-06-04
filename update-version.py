#!/usr/bin/env python
from __future__ import annotations

from ast import AST, Assign, Constant, Name, NodeTransformer, Store, parse, unparse
from importlib.metadata import version as get_version
from pathlib import Path

if __name__ != '__main__':
    raise ImportError("This cannot be imported")


class RewriteVersion(NodeTransformer):
    def visit_Assign(self, node: Assign):
        match node:
            case Assign(
                targets=[Name(id="__version__", ctx=Store())],
                value=Constant(value=_v),
                lineno=lineno,
                col_offset=col_offset
            ):
                version = get_version("caffeinate")
                return Assign(
                    targets=[Name(id="__version__", ctx=Store())],
                    value=Constant(value=version),
                    lineno=lineno,
                    col_offset=col_offset
                )

            case _:
                return self.generic_visit(node)

parent = Path(__file__).parent
module_file = parent / "caffeinate" / "__init__.py"
tree = parse(module_file.read_text())
tree = RewriteVersion().visit(parse(module_file.read_text()))
assert isinstance(tree, AST)

module_file.write_text(unparse(tree) + "\n")
print(f"Updated {module_file.relative_to(parent)}")
