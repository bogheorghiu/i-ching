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
in the same file count, and at a wrapper's call site only the arguments bound to a parameter
that reaches the wrapper's own exec call), with variables bound anywhere in the file resolved,
or as a sibling import. A file that does not parse, or whose analysis hits a size limit, is scanned as text.
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
    counts (for a wrapper, under the arguments that reach its exec call: see call_args), with names resolved through every binding in the file (assignment, with ... as,
    for, defaults), and Path(a, b), os.path.join, a / b, a + b and f-strings also joined. Each
    argument is then read like a shell line, so `npm run x` and `make` are followed."""
    try:
        tree = ast.parse(text)
        return _py_exec_refs(tree, here, files)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
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


def _py_exec_refs(tree, here: str, files: set) -> set:
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

    def is_exec(call) -> bool:
        last = _callee(call.func).split(".")[-1]
        if _is_exec_name(last) or last in exec_names:
            return True
        return any(isinstance(a, (ast.Name, ast.Attribute)) and
                   (_is_exec_name(_callee(a).split(".")[-1]) or _callee(a).split(".")[-1] in exec_names)
                   for a in call.args + [k.value for k in call.keywords])

    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    aliases = set(exec_names)
    changed = True
    while changed:   # wrappers: a function that makes an exec-like call is exec-like
        changed = False
        for f in funcs:
            if f.name not in exec_names and \
                    any(isinstance(n, ast.Call) and is_exec(n) for n in ast.walk(f)):
                exec_names.add(f.name)
                changed = True
    wrappers = {name: [f for f in funcs if f.name == name]
                for name in exec_names - aliases if not _is_exec_name(name)}
    flows = {id(f): set() for fs in wrappers.values() for f in fs}   # params reaching an exec call

    def names_in(node):
        return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}

    def call_args(call):
        """The arguments of an exec-like call that can run something. For a call to a wrapper,
        only those bound to a parameter that reaches the wrapper's own exec call; a * or **
        argument counts whole unless no parameter reaches it."""
        every = call.args + [k.value for k in call.keywords]
        last = _callee(call.func).split(".")[-1]
        if last not in wrappers or any(isinstance(a, (ast.Name, ast.Attribute)) and
                                       _callee(a).split(".")[-1] in exec_names for a in every):
            return every   # an exec call itself, an alias of one, or a handoff (map(f, ...))
        out = []
        for f in wrappers[last]:
            flow, a = flows[id(f)], f.args
            if not flow:
                continue
            if any(isinstance(x, ast.Starred) for x in call.args) or any(k.arg is None for k in call.keywords):
                return every
            pos = [p.arg for p in a.posonlyargs + a.args]
            if isinstance(call.func, ast.Attribute) and pos[:1] in (["self"], ["cls"]):
                pos = pos[1:]
            for i, x in enumerate(call.args):
                if (pos[i] if i < len(pos) else a.vararg and a.vararg.arg) in flow:
                    out.append(x)
            named = {p.arg for p in a.args + a.kwonlyargs}
            for k in call.keywords:
                if (k.arg if k.arg in named else a.kwarg and a.kwarg.arg) in flow:
                    out.append(k.value)
        return out

    def local_pairs(f):
        pairs = []
        for node in ast.walk(f):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) and node.value is not None:
                pairs += [(t, node.value) for t in (node.targets if isinstance(node, ast.Assign) else [node.target])]
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                pairs.append((node.target, node.iter))
            elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                pairs.append((node.optional_vars, node.context_expr))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                    isinstance(node.func.value, (ast.Name, ast.Attribute)):
                pairs.append((node.func.value, node))   # cmd.append(extra) feeds extra into cmd
        return [(names_in(t), names_in(v)) for t, v in pairs]

    pairs_of = {id(f): local_pairs(f) for fs in wrappers.values() for f in fs}
    changed = True
    while changed:   # which parameters reach an exec call, through local names and inner wrappers
        changed = False
        for fs in wrappers.values():
            for f in fs:
                need = set()
                for n in ast.walk(f):
                    if isinstance(n, ast.Call) and is_exec(n):
                        for x in call_args(n):
                            need |= names_in(x)
                grew = True
                while grew:
                    grew = False
                    for targets, values in pairs_of[id(f)]:
                        if targets & need and not values <= need:
                            need |= values
                            grew = True
                a = f.args
                params = {p.arg for p in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if p}
                if not need & params <= flows[id(f)]:
                    flows[id(f)] |= need & params
                    changed = True

    def product(parts, sep):
        out = {sep.join(c) for c in itertools.islice(itertools.product(*parts), 64)}
        if any(len(v) > 4096 for v in out):
            raise MemoryError("candidate value too long")
        return out

    budget = [100000]   # node visits; past it, the whole file falls back to the text scan
    memo = {}

    def strings(node, seen):
        """Values a node may hold: its own string, a joined path, or a resolved name's values."""
        budget[0] -= 1
        if budget[0] < 0:
            raise MemoryError("analysis budget spent")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.Name):
            if node.id in seen:
                return {"$"}
            if len(seen) > 50:   # past this, the whole file falls back to the text scan
                raise RecursionError("name chain too deep")
            if node.id in memo:
                return memo[node.id]
            out = set()
            for v in bound.get(node.id, []):
                out |= deep(v, seen | {node.id})
            memo[node.id] = out = out or {"$"}   # unknown value: candidates() drops a "$" prefix
            return out
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
            if len(out) > 4096:
                raise MemoryError("too many candidate values")
        return out

    def argv_lines(node, seen):
        """A list argument (or a name bound to one) read as one command line, for npm run / make."""
        if isinstance(node, (ast.List, ast.Tuple)):
            return {" ".join(sorted(strings(e, seen) or {"$"})[0] for e in node.elts)}
        if isinstance(node, ast.Name) and node.id not in seen:
            out = set()
            for v in bound.get(node.id, []):
                out |= argv_lines(v, seen | {node.id})
            return out
        return set()

    found = set()
    for call in ast.walk(tree):
        if not (isinstance(call, ast.Call) and is_exec(call)):
            continue
        for arg in call_args(call):
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
        # A wrapper's call site counts only the arguments that reach the wrapper's own exec call;
        # expected-output strings handed to a test wrapper are data.
        ("scripts/test_x.py", 'import subprocess, sys\nREADME = "# Demo"\n'
         'def run_plugin(manifest=None, readme=README, expect=""):\n'
         '    subprocess.run([sys.executable, "scripts/x.sh", "tmp"])\n'
         'run_plugin(expect="missing README.md")\n'
         'for kw in [{"readme": None, "expect": "missing README.md"}]:\n    run_plugin(**kw)\n',
         {"scripts/x.sh"}, {"README.md"}),
        ("scripts/test_x.py", 'import subprocess\ndef go(script, expect=""):\n    cmd = ["bash", script]\n'
         '    subprocess.run(cmd)\ngo("scripts/x.sh", expect="missing README.md")\n', {"scripts/x.sh"}, {"README.md"}),
        ("scripts/test_x.py", 'import subprocess\ndef go(extra):\n    cmd = ["bash"]\n    cmd.append(extra)\n'
         '    subprocess.run(cmd)\ngo("scripts/x.sh")\n', {"scripts/x.sh"}, set()),
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
