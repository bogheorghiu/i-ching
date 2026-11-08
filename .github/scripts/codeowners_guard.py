#!/usr/bin/env python3
"""CODEOWNERS tripwire: fails when something that runs or loads without a reader is not owned.

A tripwire, not the gate. The gate is the ruleset on the default branch requiring code-owner
review; this check makes a careless agent (Claude or not) see the gap before it asks for a
merge, in CI, where it does not depend on which harness or plugins the agent runs.

It fails when:
1. A tracked file matches MUST_OWN (files agent harnesses load by themselves, code that runs on
   install, commit, push or folder-open, dependency manifests) and no CODEOWNERS line owns it.
2. An owned "runner" file (a hook, workflow, git hook, MCP config, devcontainer, package.json,
   pre-commit config) names another tracked file, and that file is not owned. Followed
   transitively. Why: an owned hook that runs an unowned script runs whatever the next ungated
   PR puts in that script (the gap kit/test_protected.py closes in bogheorghiu/board-pattern).
3. The gate does not cover itself: CODEOWNERS, this script and its workflow.

Limits (say these when a green check is quoted): MUST_OWN is a list; a harness that loads a
file name not on it is not seen. References are found by text, skipping comments: a path
assembled at run time, a glob, or a directory handed to a test runner is not seen; a file named
only in an echo or a string is still reported (reword it or own the file). Skill and command
bodies under .claude/ are not read. `npm run x` is followed one level into scripts.x. Python
imports of sibling modules are followed; other languages' imports are not. Markdown is read
only for `@path` imports; package.json only for its install-time lifecycle scripts.

What counts as running a file: executing, sourcing or importing it, not checking that it exists
or using its name as test data. Python is parsed (ast): a name counts only inside the arguments
of an exec-like call (subprocess.*, os.system/exec*/spawn*, exec, eval, runpy, importlib; matched
by the call's last name, so session.run in a noxfile counts too; aliases and wrapper functions
in the same file count), with variables bound anywhere in the file resolved, or as a sibling
import. A file that does not parse, or whose analysis hits a size limit, is scanned as text.
Not seen in Python: a callable reached through getattr, a dict, or another module's wrapper.
Shell-like text (hooks, workflows, git hooks, Makefiles, JSON commands) still counts every token
except the operand of an existence test (`test -f x`, `[ -e x ]`, `[[ -d x ]]`). Other script
languages (.js, .ts, .rb, .pl, .ps1) still count every token: a false positive there is reworded
or owned.

Usage: python3 .github/scripts/codeowners_guard.py [--self-test]
Standard library only, so it runs on any runner and needs no install step.
"""
import ast
import fnmatch
import itertools
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = ".github/scripts/codeowners_guard.py"
WORKFLOW = ".github/workflows/codeowners-guard.yml"
CODEOWNERS_PATHS = [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]  # GitHub's search order

# Basename globs (match at any depth) and path prefixes that must be owned when tracked.
# Add a name here when a harness or tool you use loads or runs it unread; the reason belongs
# in AGENTS.md ("When a path gets an owner").
MUST_OWN_NAMES = [
    # Agent instructions and config, any harness.
    "CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", "AGENTS.override.md", "GEMINI.md",
    ".mcp.json", "mcp.json", ".cursorrules", ".windsurfrules", ".clinerules", ".roomodes",
    ".goosehints", ".aider.conf.yml", "opencode.json",
    # Code that runs on open, commit, push, install or environment entry.
    ".pre-commit-config.yaml", ".envrc", ".devcontainer.json", ".gitmodules", ".gitattributes",
    ".lfsconfig", ".tool-versions", ".mise.toml", "mise.toml",
    # Dependency manifests, lockfiles, package-manager config.
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", ".yarnrc",
    ".yarnrc.yml", "pnpm-lock.yaml", "pnpm-workspace.yaml", ".pnpmfile.cjs", "bun.lock",
    "bun.lockb", "bunfig.toml", ".npmrc", "requirements*.txt", "pyproject.toml", "setup.py",
    "setup.cfg", "uv.lock", "poetry.lock", "Pipfile", "Pipfile.lock", "pip.conf",
    "Cargo.toml", "Cargo.lock", "go.mod", "go.sum", "Gemfile", "Gemfile.lock",
    # Exclusions that keep key material and the PII denylist out of history, and the secret
    # scanner's own allowlists (an agent could allowlist its own leaked key).
    ".gitignore", ".gitleaks.toml", ".gitleaksignore",
]
MUST_OWN_DIRS = [".claude", ".claude-plugin", ".gemini", ".codex", ".cursor", ".windsurf",
                 ".continue", ".roo", ".kiro", ".junie", ".amazonq", ".opencode", ".githooks",
                 ".husky", ".devcontainer", ".vscode", ".idea", ".cargo", ".yarn"]
ROOT_ONLY_DIRS = [".github"]  # GitHub reads only the root .github/; nested copies are inert

# Owned files whose text can name a file that then runs.
RUNNER_NAMES = ["settings.json", "settings.local.json", ".mcp.json", "mcp.json", "hooks.json",
                "package.json", ".pre-commit-config.yaml", "devcontainer.json",
                ".devcontainer.json", "tasks.json", ".envrc", ".gitmodules",
                "Makefile", "makefile", "GNUmakefile", "justfile", "Justfile", "tox.ini", "noxfile.py"]
RUNNER_DIRS = [".github/workflows", ".github/actions", ".githooks", ".husky", ".claude/hooks"]
INSTRUCTION_NAMES = ["CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", "AGENTS.override.md", "GEMINI.md"]
SCRIPT_EXT = (".sh", ".bash", ".py", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".ps1")
LIFECYCLE = ("preinstall", "install", "postinstall", "prepare", "preprepare", "postprepare",
             "prepublish", "prepack", "postpack")
# Command words that run a fixed file without naming it.
TOOL_FILES = {"make": ["Makefile", "makefile", "GNUmakefile"], "just": ["justfile", "Justfile"],
              "tox": ["tox.ini"], "nox": ["noxfile.py"]}
PATH_TOKEN = re.compile(r"[A-Za-z0-9_.${}()/@+-]+")
COMMENT = re.compile(r"^\s*(#|//)")
TRAILING_COMMENT = re.compile(r"\s+(#|//)\s.*$")
RUN_SCRIPT = re.compile(r"\b(?:npm|pnpm|yarn|bun)\s+(?:run(?:-script)?\s+)?([A-Za-z0-9:_.-]+)")
# Shell existence tests: their operand is checked, not run.
_OPERAND = r"""(?:"[^"$`]*"|'[^']*'|[^\s;&|<>()`$"']+)"""   # no substitution, stops at ; & |
EXISTENCE_TEST = re.compile(r"((?:^|[;&|(`]|\b(?:if|then|elif|while|until|do|!)\s)\s*)"
                            r"(?:test\s+-[efdrsxLh]\s+" + _OPERAND + r"(?=$|[\s;&|)])"
                            r"|\[\[?\s+-[efdrsxLh]\s+" + _OPERAND + r"\s+\]\]?)")
# Python calls whose arguments run, source or import a file, by the callee's last name.
PY_EXEC_NAMES = {"run", "call", "check_call", "check_output", "Popen", "system", "popen",
                 "getoutput", "getstatusoutput", "startfile", "run_path", "run_module", "exec",
                 "execfile", "import_module", "__import__", "spec_from_file_location",
                 "SourceFileLoader", "load_source", "eval", "compile", "main"}

# Method calls that put their arguments into the container they are called on.
PY_MUTATORS = {"append", "extend", "insert", "appendleft", "extendleft", "add", "update",
               "setdefault", "put", "put_nowait", "__setitem__"}


def tracked():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p for p in out.decode().split("\0") if p]


def pattern_regex(pat: str) -> re.Pattern:
    """CODEOWNERS uses gitignore rules: a leading or inner "/" anchors to the root, otherwise the
    pattern matches at any depth; a trailing "/" means a directory; `*` stays in one segment,
    `**` crosses segments. A pattern naming a directory covers everything under it."""
    is_dir = pat.endswith("/")
    body = pat.strip("/")
    anchored = pat.startswith("/") or "/" in body
    out, i = "", 0
    while i < len(body):
        if body.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif body.startswith("/**", i) and i + 3 == len(body):
            out, i = out + "/.*", i + 3
        elif body[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif body[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(body[i]), i + 1
    head = "^" if anchored else "^(?:.*/)?"
    # GitHub: `docs/*` matches docs/a.md but not docs/x/a.md; a name without a wildcard in its
    # last segment also covers everything under it when it is a directory.
    last = body.rsplit("/", 1)[-1]
    tail = "/.*$" if is_dir else ("$" if ("*" in last or "?" in last) else "(?:/.*)?$")
    return re.compile(head + out + tail)


def read_codeowners():
    for rel in CODEOWNERS_PATHS:
        f = ROOT / rel
        if f.is_file():
            rules = []
            for ln in f.read_text().splitlines():
                ln = re.split(r"\s#", ln)[0].strip()
                if ln and not ln.startswith("#"):
                    pat, *owners = ln.split()
                    rules.append((pattern_regex(pat), owners))
            return rel, rules
    return None, []


def owned(path: str, rules) -> bool:
    hit = []
    for rx, owners in rules:  # the last matching line wins; a line with no owner un-owns
        if rx.match(path):
            hit = owners
    return bool(hit)


def must_own(path: str) -> bool:
    """Case-folded: a case-insensitive clone (macOS, Windows) loads `claude.md` as CLAUDE.md,
    while CODEOWNERS matches case-sensitively, so a differently cased name must be flagged."""
    parts = path.split("/")
    name = parts[-1].lower()
    return any(fnmatch.fnmatchcase(name, n.lower()) for n in MUST_OWN_NAMES) or \
        any(d in parts[:-1] for d in MUST_OWN_DIRS) or \
        (len(parts) > 1 and parts[0] in ROOT_ONLY_DIRS)


def is_runner(path: str) -> bool:
    name = path.split("/")[-1]
    return name in RUNNER_NAMES or name in INSTRUCTION_NAMES or \
        any(path.startswith(d + "/") for d in RUNNER_DIRS)


def candidates(tok: str, here: str):
    """Repo paths a token could name: as written, relative to the file's folder, and every
    suffix after a "/" (so "$CLAUDE_PROJECT_DIR"/x.sh, $(git rev-parse --show-toplevel)/x.sh and
    $ROOT/x.sh all reach x.sh)."""
    tok = tok.strip("\"'()").lstrip("@")
    outs = {tok, posixpath.join(here, tok), tok.lstrip("/")}   # "$X"/a.sh splits at the quote
    # Only a variable or command-substitution prefix is dropped, not any directory, so that
    # `docs/site/index.html` or a URL does not also "name" a root `index.html`.
    for i, ch in enumerate(tok):
        if ch == "/" and re.search(r"[$)\"']", tok[:i]):
            outs.add(tok[i + 1:].lstrip("\"'"))
    return {posixpath.normpath(o) for o in outs if o and "$" not in posixpath.normpath(o)}


def references(path: str, files: set) -> set:
    """Tracked files a runner or script names, or that a command word in it runs."""
    try:
        text = (ROOT / path).read_text(errors="replace")
    except OSError:
        return set()
    return refs_in_text(path, text, files)


def refs_in_text(path: str, text: str, files: set) -> set:
    """references() on given text, so the self-test can feed it fixtures."""
    here = posixpath.dirname(path)
    name = path.split("/")[-1]
    if name in INSTRUCTION_NAMES:   # instructions: only `@path` imports load another file
        found = set()
        for m in re.finditer(r"(?<![\w`])@([A-Za-z0-9_.~/-]+)", text):
            found |= {c for c in candidates(m.group(1), here) if c in files}
        return found - {path}
    if name == "package.json":       # only what runs at install, unread
        try:
            scripts = json.loads(text).get("scripts", {}) or {}
        except ValueError:
            scripts = {}
        text = "\n".join(v for k, v in scripts.items() if k in LIFECYCLE and isinstance(v, str))
    if path.endswith(".py"):
        found = py_exec_refs(text, here, files)
        if found is not None:
            return found | py_sibling_imports(text, here, files)
    lines = [TRAILING_COMMENT.sub("", ln) for ln in text.splitlines() if not COMMENT.match(ln)]
    found = set()
    for ln in lines:
        found |= line_refs(ln, here, name, files)
    if path.endswith(".py"):   # unparsable Python: the text scan above, plus imports
        found |= py_sibling_imports(text, here, files)
    return found - {path}


def line_refs(ln: str, here: str, name: str, files: set) -> set:
    """Tracked files one shell-like line names (outside existence tests) or runs by command word."""
    found = set()
    for tok in PATH_TOKEN.findall(EXISTENCE_TEST.sub(r"\1 ", ln)):
        found |= {c for c in candidates(tok, here) if c in files}
    for word, targets in TOOL_FILES.items():   # at command position only, not in prose
        if re.search(r"(?:^|run:|[;&|(`]|&&|\|\||-)\s*" + word + r"(?:\s+[\w./-]+)*\s*$", ln) or \
                re.search(r"(?:^|run:|[;&|(`]|&&|\|\||-)\s*" + word + r"\s*(?:[;&|)`]|$)", ln):
            found |= {t for t in targets if t in files}
    if name != "package.json" and "package.json" in files:   # `npm run x` runs scripts.x
        for m in RUN_SCRIPT.finditer(ln):
            found |= run_script_refs(m.group(1), files)
    return found


def py_sibling_imports(text: str, here: str, files: set) -> set:
    found = set()
    for m in re.finditer(r"^\s*(?:from|import)\s+\.?([A-Za-z_][A-Za-z0-9_]*)", text, re.M):
        cand = posixpath.normpath(posixpath.join(here, m.group(1) + ".py"))
        if cand in files:
            found.add(cand)
    return found


def py_exec_refs(text: str, here: str, files: set):
    """Tracked files an exec-like call in Python source runs, or None to fall back to the text
    scan (the source does not parse, or the analysis hits a limit). Exec-like: a call whose last
    name is in PY_EXEC_NAMES or contains "exec"/"spawn"; a name imported as an alias of one; a
    function in this file whose body makes one (to a fixpoint, so wrappers count); a call handed
    one as an argument (map(subprocess.run, ...)). Every string anywhere under its arguments
    counts, with names resolved through every binding in the file (assignment, with ... as,
    for, defaults), and Path(a, b), os.path.join, a / b, a + b and f-strings also joined. Each
    argument is then read like a shell line, so `npm run x` and `make` are followed."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None
    # The bindings calls make (_add_call_flows) only add values, so they can push a large file
    # past a limit it met without them; that file is then analysed without them rather than
    # dropped to the text scan, which misses joined paths.
    for call_flows in (True, False):
        try:
            return _py_exec_refs(ast.parse(text), here, files, call_flows)
        except (ValueError, RecursionError, MemoryError):
            continue
    return None


def _callee(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _is_exec_name(last: str) -> bool:
    return last in PY_EXEC_NAMES or "exec" in last.lower() or "spawn" in last.lower()


def _names(node) -> set:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _add_call_flows(tree, bound: dict) -> None:
    """Bindings that calls make, added to `bound` (only ever added, so nothing reported before
    stops being reported): a plain call's arguments to the parameters of the one function of
    that name defined in this file (a method call obj.f(...) is not followed: binding it to every
    def of that name made value sets explode), and a mutating
    method call's arguments (CASES.append(x), also through `f = CASES.append` or
    `map(CASES.append, xs)`) to every name in the receiver and every name it was assigned from."""
    defs = {}
    for f in ast.walk(tree):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(f.name, []).append(f.args)
    calls = [c for c in ast.walk(tree) if isinstance(c, ast.Call)]
    for c in calls:
        if not isinstance(c.func, ast.Name) or len(defs.get(c.func.id, [])) != 1:
            continue
        for a in defs[c.func.id]:
            pos = [p.arg for p in a.posonlyargs + a.args]
            named = pos + [p.arg for p in a.kwonlyargs]
            extra = [p.arg for p in (a.vararg, a.kwarg) if p]
            if any(isinstance(x, ast.Starred) for x in c.args) or any(k.arg is None for k in c.keywords):
                for x in c.args + [k.value for k in c.keywords]:   # unknown alignment: every parameter
                    for p in named + extra:
                        bound.setdefault(p, []).append(x)
                continue
            for i, x in enumerate(c.args):
                for p in ([pos[i]] if i < len(pos) else extra):
                    bound.setdefault(p, []).append(x)
            for k in c.keywords:
                for p in ([k.arg] if k.arg in named else extra):
                    bound.setdefault(p, []).append(k.value)
    via = {}   # f = CASES.append: calling f mutates CASES
    for n, vs in bound.items():
        for v in vs:
            if isinstance(v, ast.Attribute) and v.attr in PY_MUTATORS:
                via.setdefault(n, set()).update(_names(v.value))
    mutated = []   # (receiver names, value nodes put into it)
    for c in calls:
        args = c.args + [k.value for k in c.keywords]
        if isinstance(c.func, ast.Attribute) and c.func.attr in PY_MUTATORS:
            mutated.append((_names(c.func.value), args))
        elif isinstance(c.func, ast.Name) and c.func.id in via:
            mutated.append((via[c.func.id], args))
        for a in args:   # map(CASES.append, xs): the other arguments may go in
            if isinstance(a, ast.Attribute) and a.attr in PY_MUTATORS:
                mutated.append((_names(a.value), [x for x in args if x is not a]))
    holders = {}   # x = y = []: both names hold the one value
    for n, vs in bound.items():
        for v in vs:
            holders.setdefault(id(v), []).append(n)
    sources = {n: [v.id for v in vs if isinstance(v, ast.Name)] + [m for v in vs for m in holders[id(v)]]
               for n, vs in bound.items()}
    for names, values in mutated:
        todo, done = list(names), set()
        while todo:
            n = todo.pop()
            if n not in done:
                done.add(n)
                bound.setdefault(n, []).extend(values)
                todo += sources.get(n, [])


def _py_exec_refs(tree, here: str, files: set, call_flows: bool = True) -> set:
    bound = {}   # name -> value nodes it may hold
    exec_names = set()
    for node in ast.walk(tree):
        pairs = []
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) and node.value is not None:
            pairs = [(t, node.value) for t in (node.targets if isinstance(node, ast.Assign) else [node.target])]
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            pairs = [(node.target, node.iter)]
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            pairs = [(node.optional_vars, node.context_expr)]
        elif isinstance(node, ast.arguments):
            pos = node.posonlyargs + node.args
            pairs = list(zip(pos[len(pos) - len(node.defaults):], node.defaults))
            pairs += [(a, d) for a, d in zip(node.kwonlyargs, node.kw_defaults) if d is not None]
        elif isinstance(node, ast.ImportFrom):
            exec_names |= {al.asname for al in node.names if al.asname and _is_exec_name(al.name)}
        for target, value in pairs:   # launch = subprocess.run makes `launch` exec-like
            if isinstance(value, (ast.Name, ast.Attribute)) and isinstance(target, ast.Name) and \
                    _is_exec_name(_callee(value).split(".")[-1]):
                exec_names.add(target.id)
            names = [target.arg] if isinstance(target, ast.arg) else \
                [n.id for n in ast.walk(target) if isinstance(n, ast.Name)]
            for n in names:
                bound.setdefault(n, []).append(value)

    if call_flows:
        _add_call_flows(tree, bound)

    def is_exec(call) -> bool:
        last = _callee(call.func).split(".")[-1]
        if _is_exec_name(last) or last in exec_names:
            return True
        return any(isinstance(a, (ast.Name, ast.Attribute)) and
                   (_is_exec_name(_callee(a).split(".")[-1]) or _callee(a).split(".")[-1] in exec_names)
                   for a in call.args + [k.value for k in call.keywords])

    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    changed = True
    while changed:   # wrappers: a function that makes an exec-like call is exec-like
        changed = False
        for f in funcs:
            if f.name not in exec_names and \
                    any(isinstance(n, ast.Call) and is_exec(n) for n in ast.walk(f)):
                exec_names.add(f.name)
                changed = True

    def product(parts, sep):
        out = {sep.join(c) for c in itertools.islice(itertools.product(*parts), 64)}
        if any(len(v) > 4096 for v in out):
            raise MemoryError("candidate value too long")
        return out

    budget = [300000]   # node visits; past it, the whole file falls back to the text scan
    vals = {}   # name -> values it may hold, filled by resolve_names() before any lookup

    def strings(node, seen):
        """Values a node may hold: its own string, a joined path, or a resolved name's values."""
        budget[0] -= 1
        if budget[0] < 0:
            raise MemoryError("analysis budget spent")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.Name):
            return vals.get(node.id) or {"$"}   # unknown value: candidates() drops a "$" prefix
        if isinstance(node, ast.JoinedStr):
            return product([(strings(v.value, seen) if isinstance(v, ast.FormattedValue)
                             else strings(v, seen)) or {"$"} for v in node.values], "")
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
            return product([strings(node.left, seen) or {"$"}, strings(node.right, seen) or {"$"}],
                           "/" if isinstance(node.op, ast.Div) else "")
        if isinstance(node, ast.Call):
            last = _callee(node.func).split(".")[-1]
            if last in ("Path", "PurePath", "PosixPath", "join") and node.args:
                return product([strings(a, seen) or {"$"} for a in node.args], "/")
            if last in ("str", "fspath", "abspath", "realpath", "resolve") and node.args:
                return strings(node.args[0], seen)
        return set()

    def deep(node, seen):
        out = set()
        for sub in ast.walk(node):
            out |= strings(sub, seen)
            if len(out) > 16384:
                raise MemoryError("too many candidate values")
        return out

    argvs = {}   # name -> command lines it may hold, filled by resolve_names()

    def argv_line(node):
        return " ".join(min(strings(e, frozenset()) or {"$"}) for e in node.elts)

    def argv_lines(node, seen):
        """A list argument (or a name bound to one) read as one command line, for npm run / make."""
        if isinstance(node, (ast.List, ast.Tuple)):
            return {argv_line(node)}
        if isinstance(node, ast.Name):
            return argvs.get(node.id, set())
        return set()

    def resolve_names():
        """Every name's values, to a fixed point, so no answer depends on the order of lookups (a
        recursive walk with a cache did: a value computed while a cycle was cut short got cached).
        A name is re-evaluated when a name its bindings use changes; each may change at most 8
        times (a string built in a loop grows forever), so the loop ends."""
        users = {}
        for n, vs in bound.items():
            for v in vs:
                for m in {x.id for x in ast.walk(v) if isinstance(x, ast.Name)}:
                    users.setdefault(m, set()).add(n)
        work, queued, changes = list(bound), set(bound), {}
        while work:
            n = work.pop(0)
            queued.discard(n)
            if changes.get(n, 0) >= 8:
                continue
            new = set()
            for v in bound[n]:
                new |= deep(v, frozenset())
            if new != vals.get(n, set()):
                vals[n] = new
                changes[n] = changes.get(n, 0) + 1
                for m in users.get(n, ()):
                    if m not in queued:
                        work.append(m)
                        queued.add(m)

    resolve_names()
    # Command lines through names, to a fixed point too: a recursive walk over the names followed
    # every path through them (exponential once names link to each other), with no budget.
    line_users = {}
    for n, vs in bound.items():
        for v in vs:
            if isinstance(v, ast.Name):
                line_users.setdefault(v.id, set()).add(n)
    work, queued, changes = list(bound), set(bound), {}
    while work:
        n = work.pop(0)
        queued.discard(n)
        if changes.get(n, 0) >= 8:
            continue
        new = set()
        for v in bound[n]:
            new |= argv_lines(v, frozenset())
        if len(new) > 16384:
            raise MemoryError("too many command lines")
        if new != argvs.get(n, set()):
            argvs[n] = new
            changes[n] = changes.get(n, 0) + 1
            for m in line_users.get(n, ()):
                if m not in queued:
                    work.append(m)
                    queued.add(m)
    found = set()
    for call in ast.walk(tree):
        if not (isinstance(call, ast.Call) and is_exec(call)):
            continue
        for arg in call.args + [k.value for k in call.keywords]:
            lines = deep(arg, frozenset()) | argv_lines(arg, frozenset())
            for ln in lines:
                found |= line_refs(ln, here, "", files)
    return found


def run_script_refs(script: str, files: set) -> set:
    """Tracked files the root package.json script `script` names (one level)."""
    try:
        body = (json.loads((ROOT / "package.json").read_text()).get("scripts") or {}).get(script)
    except (OSError, ValueError):
        return set()
    if not isinstance(body, str):
        return set()
    found = {"package.json"}
    for tok in PATH_TOKEN.findall(body):
        found |= {c for c in candidates(tok, ".") if c in files}
    return found


def follows(path: str) -> bool:
    """Files whose own text is followed further: runners and scripts, never prose or data."""
    return is_runner(path) or path.endswith(SCRIPT_EXT) or "." not in path.split("/")[-1]


def check(files):
    problems = []
    rel, rules = read_codeowners()
    if rel is None:
        return ["no CODEOWNERS file: nothing is gated"]
    fileset = set(files)
    for p in [rel, SELF, WORKFLOW]:
        if not owned(p, rules):
            problems.append(f"the gate does not cover itself: {p}")
    for n in MUST_OWN_NAMES:   # the list and CODEOWNERS must not drift apart
        for p in (n.replace("*", "x"), "a/" + n.replace("*", "x")):
            if not owned(p, rules):
                problems.append(f"CODEOWNERS has no line for {n} (guard list), checked as {p}")
    for d in MUST_OWN_DIRS + ROOT_ONLY_DIRS:
        if not owned(f"{d}/x", rules):
            problems.append(f"CODEOWNERS has no line for {d}/ (guard list)")
    for p in files:
        if must_own(p) and not owned(p, rules):
            problems.append(f"unowned file that runs or loads unread: {p}")
    seen, todo = set(), [p for p in files if is_runner(p) and owned(p, rules)]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        if p == SELF:   # its name lists and self-test strings are data, not things it runs
            continue
        for ref in references(p, fileset):
            if not owned(ref, rules):
                problems.append(f"{p} runs or names {ref}, which is not owned")
            if follows(ref):
                todo.append(ref)
    return sorted(set(problems))


def self_test():
    cases = [
        (".claude/", ".claude/settings.json", True), (".claude/", "a/b/.claude/x.md", True),
        ("/.github/", ".github/workflows/x.yml", True), ("/.github/", "x/.github/y", False),
        ("CLAUDE.md", "docs/CLAUDE.md", True), ("/CLAUDE.md", "docs/CLAUDE.md", False),
        ("docs/*.md", "docs/a.md", True), ("docs/*.md", "docs/x/a.md", False),
        ("requirements*.txt", "svc/requirements-dev.txt", True), ("**/logs", "a/b/logs/c", True),
        ("/src/**/key.ts", "src/a/b/key.ts", True), ("scripts", "scripts/run.sh", True),
        ("docs/*", "docs/a.md", True), ("docs/*", "docs/x/a.md", False),
    ]
    bad = [(p, f, want) for p, f, want in cases if bool(pattern_regex(p).match(f)) != want]
    rules = [(pattern_regex("/.github/"), ["@o"]), (pattern_regex("/.github/free.md"), [])]
    if owned(".github/free.md", rules) or not owned(".github/x", rules):
        bad.append(("last match wins", "", ""))
    here = ".claude"
    want = {"scripts/x.sh"}
    for tok in ['"$CLAUDE_PROJECT_DIR"/scripts/x.sh', "$(git rev-parse --show-toplevel)/scripts/x.sh",
                "../scripts/x.sh", "@scripts/x.sh"]:
        if not want <= candidates(tok, here):
            bad.append(("candidates", tok, sorted(candidates(tok, here))))
    for tok in PATH_TOKEN.findall('"command": "\\"$CLAUDE_PROJECT_DIR\\"/scripts/x.sh"'):
        want -= candidates(tok, ".")
    if want:
        bad.append(("quoted hook path, as tokenized", "scripts/x.sh", ""))
    if "index.html" in candidates("docs/site/index.html", ".") | candidates("https://x.org/a/index.html", "."):
        bad.append(("suffix over-match", "index.html", ""))
    if not must_own("docs/claude.md") or must_own("x/.github/y") or not must_own(".github/y"):
        bad.append(("must_own case/anchor", "", ""))
    fx = {"README.md", "LICENSE", "scripts/x.sh"}
    exists = 'from pathlib import Path\nd = "plug"\nok = Path(d, "README.md").exists() and Path(d, "LICENSE").is_file()\n'
    if refs_in_text("scripts/check.py", exists, fx) & {"README.md", "LICENSE"}:
        bad.append(("existence check counted as running", "README.md/LICENSE", ""))
    runs = 'import subprocess\nsubprocess.run(["bash", "scripts/x.sh"], check=True)\n'
    if "scripts/x.sh" not in refs_in_text("scripts/check.py", runs, fx):
        bad.append(("subprocess.run of a script not counted", "scripts/x.sh", ""))
    kept = [   # rule changes must not lose these
        (".githooks/pre-push", '[ -f README.md ] && bash scripts/x.sh\n', {"scripts/x.sh"}, {"README.md"}),
        ("scripts/check.py", 'import subprocess\nCMD = ["bash", "scripts/x.sh"]\nsubprocess.call(CMD)\n',
         {"scripts/x.sh"}, set()),
        ("scripts/check.py", 'import os, subprocess\nfrom pathlib import Path\nROOT = Path(__file__).parent\n'
         'def main():\n    s = str(ROOT / "scripts/x.sh")\n    subprocess.run(["bash", s])\n', {"scripts/x.sh"}, set()),
        ("scripts/check.py", 'import os\nos.system(f"{os.getcwd()}/scripts/x.sh --fast")\n', {"scripts/x.sh"}, set()),
        ("scripts/check.py", 'import runpy\nrunpy.run_path("scripts/x.sh")\nopen("LICENSE").read()\n',
         {"scripts/x.sh"}, {"LICENSE"}),
        ("scripts/check.py", 'def broken(:\n  "scripts/x.sh"\n', {"scripts/x.sh"}, set()),
        (".githooks/pre-push", 'test -f /dev/null;./scripts/x.sh\n', {"scripts/x.sh"}, set()),
        (".githooks/pre-push", 'test -f "$(./scripts/x.sh)"\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'from subprocess import run as launch\nlaunch(["bash", "scripts/x.sh"])\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import os\nos.posix_spawn("scripts/x.sh", [], os.environ)\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'with open("scripts/x.sh") as f:\n    exec(f.read())\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'eval(compile(open("scripts/x.sh").read(), "p", "exec"))\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\ndef sh(cmd):\n    subprocess.run(cmd, shell=True)\nsh("bash scripts/x.sh")\n',
         {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\nfor c in [["bash", "scripts/x.sh"]]:\n    subprocess.run(c)\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\nlist(map(subprocess.run, [["bash", "scripts/x.sh"]]))\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\nv0 = "scripts/x.sh"\n' + "".join(f"v{i} = v{i-1}\n" for i in range(1, 600))
         + 'subprocess.run(["bash", v599])\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\n' + "".join(f'a = "{i}"\n' for i in range(10))
         + 'subprocess.run(a + a + a + a + a + a + a + a + " scripts/x.sh")\n', {"scripts/x.sh"}, set()),
        (".githooks/pre-push", 'set -- test -f scripts/x.sh\n"$3"\n', {"scripts/x.sh"}, set()),
        (".githooks/pre-push", 'if [ -f README.md ]; then echo ok; fi\n', set(), {"README.md"}),
        ("noxfile.py", 'import subprocess\nlaunch = subprocess.run\nlaunch(["bash", "scripts/x.sh"])\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import pytest\npytest.main(["scripts/x.sh"])\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\nCMD = "scripts/x.sh"\nsubprocess.run(f"bash {CMD}")\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\nS = ["scripts/x.sh"]\nfor p in S:\n    subprocess.run(p)\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\na0 = "x"\n' + "".join(f"a{i} = a{i-1} + a{i-1}\n" for i in range(1, 36))
         + 'subprocess.run(a35)\nsubprocess.run("scripts/x.sh")\n', {"scripts/x.sh"}, set()),
        # Values must not depend on which call is analysed first: d holds "scripts" after the swap.
        ("noxfile.py", 'import subprocess\nd = "docs"\ne = "scripts"\nd, e = e, d\nsubprocess.run(["echo", e])\n'
         'subprocess.run(["bash", d + "/x.sh"])\n', {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\nd = "docs"\ne = "scripts"\nd, e = e, d\nsubprocess.run(["bash", e, d + "/x.sh"])\n',
         {"scripts/x.sh"}, set()),
        ("noxfile.py", 'import subprocess\nb = a + "/x.sh"\na = "scripts"\nsubprocess.run(["bash", b])\n', {"scripts/x.sh"}, set()),
        # Values put into a container by a method call count, through aliases and local helpers.
        ("scripts/check.py", 'import subprocess\nCASES = [("a", "README.md")]\nCASES.append(("b", "scripts/x.sh"))\n'
         'for n, c in CASES:\n    subprocess.run(["bash", c])\n', {"scripts/x.sh"}, set()),
        ("scripts/check.py", 'import subprocess\nCASES = []\nA = CASES\nA.extend([("b", "scripts/x.sh")])\n'
         'for n, c in CASES:\n    subprocess.run(["bash", c])\n', {"scripts/x.sh"}, set()),
        ("scripts/check.py", 'import subprocess\nCASES = []\ndef add(lst, item):\n    lst.append(item)\n'
         'add(CASES, ("b", "scripts/x.sh"))\nfor n, c in CASES:\n    subprocess.run(["bash", c])\n', {"scripts/x.sh"}, set()),
        ("scripts/check.py", 'import subprocess\nCASES = []\ndef add(item):\n    CASES.append(item)\n'
         'add(("b", "scripts/x.sh"))\nfor n, c in CASES:\n    subprocess.run(["bash", c])\n', {"scripts/x.sh"}, set()),
        ("scripts/check.py", 'import subprocess\nCASES = []\nlist(map(CASES.append, [("b", "scripts/x.sh")]))\n'
         'for n, c in CASES:\n    subprocess.run(["bash", c])\n', {"scripts/x.sh"}, set()),
        ("scripts/check.py", 'import subprocess\nx = "docs"\nnames = []\nnames.append("README.md")\nsubprocess.run(["echo", x])\n',
         set(), {"README.md"}),
    ]
    for path, text, want_in, want_out in kept:
        got = refs_in_text(path, text, fx)
        if not want_in <= got or got & want_out:
            bad.append(("refs_in_text", path, text[:120], sorted(got)))
    for b in bad:
        print("self-test FAILED:", b)
    return not bad


def main():
    if "--self-test" in sys.argv:
        sys.exit(0 if self_test() else 1)
    if not self_test():
        sys.exit("the guard's own matcher is broken; fix it before trusting a green run")
    problems = check(tracked())
    for p in problems:
        print("::error::" + p if "GITHUB_ACTIONS" in __import__("os").environ else p)
    if problems:
        print("\nFix: add the CODEOWNERS line in its own PR (the owner reviews it; see AGENTS.md).\n"
              "Never edit this guard or its lists to get green: that PR is owner-gated too.")
        sys.exit(1)
    print("codeowners-guard: every file that runs or loads unread is owned.")


if __name__ == "__main__":
    main()
