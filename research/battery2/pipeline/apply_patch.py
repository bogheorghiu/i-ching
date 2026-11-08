#!/usr/bin/env python3
"""Apply '### replace <fn>' / '### add <fn> after <fn>' blocks from a model's patch, by whole top-level function.
Replacements first, then additions; an addition whose anchor is missing goes just before main()."""
import ast, re, sys, textwrap
path, patch_path = sys.argv[1], sys.argv[2]
text = open(path).read()
blocks = re.findall(r"^### (replace|add) (\w+)(?: after (\w+))?\s*\n```python\n(.*?)\n```", open(patch_path).read(), re.S | re.M)
blocks = [(k, n, a, textwrap.dedent(c).rstrip("\n") + "\n") for k, n, a, c in blocks]
def spans(t):
    return {n.name: (min([d.lineno for d in n.decorator_list] + [n.lineno]) - 1, n.end_lineno)
            for n in ast.parse(t).body if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))}
def splice(t, a, b, new):
    lines = t.splitlines(keepends=True); return "".join(lines[:a] + [new] + lines[b:])
for k, n, a, c in sorted(blocks, key=lambda b: b[0] != 'replace'):
    sp = spans(text)
    if k == 'replace' and n in sp: text = splice(text, sp[n][0], sp[n][1], c); print('replaced', n)
    else:
        pos = sp[a][1] if (k == 'add' and a in sp) else sp['main'][0]
        text = splice(text, pos, pos, "\n\n" + c + "\n"); print('added', n, 'after', a if a in sp else 'before main')
open(path, 'w').write(text)
