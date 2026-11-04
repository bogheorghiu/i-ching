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

Usage: python3 .github/scripts/codeowners_guard.py [--self-test]
Standard library only, so it runs on any runner and needs no install step.
"""
import fnmatch
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
    lines = [TRAILING_COMMENT.sub("", ln) for ln in text.splitlines() if not COMMENT.match(ln)]
    found = set()
    for ln in lines:
        for tok in PATH_TOKEN.findall(ln):
            found |= {c for c in candidates(tok, here) if c in files}
        for word, targets in TOOL_FILES.items():   # at command position only, not in prose
            if re.search(r"(?:^|run:|[;&|(`]|&&|\|\||-)\s*" + word + r"(?:\s+[\w./-]+)*\s*$", ln) or \
                    re.search(r"(?:^|run:|[;&|(`]|&&|\|\||-)\s*" + word + r"\s*(?:[;&|)`]|$)", ln):
                found |= {t for t in targets if t in files}
        if name != "package.json" and "package.json" in files:   # `npm run x` runs scripts.x
            for m in RUN_SCRIPT.finditer(ln):
                found |= run_script_refs(m.group(1), files)
    if path.endswith(".py"):
        for m in re.finditer(r"^\s*(?:from|import)\s+\.?([A-Za-z_][A-Za-z0-9_]*)", text, re.M):
            cand = posixpath.normpath(posixpath.join(here, m.group(1) + ".py"))
            if cand in files:
                found.add(cand)
    return found - {path}


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
