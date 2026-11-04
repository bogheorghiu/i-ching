#!/bin/bash
# Test suite for the pre-push PII guard
# Run: bash pre-push.test.sh
#
# The gate's whole job is to stop a denylisted personal name reaching a remote, so every test
# here asks one question: does a name get through, or does a clean push get blocked? The hook is
# driven exactly as git drives it — ref lines on stdin, remote name in $1.
#
# What it covers is not listed here. Every case names its own invariant in the string it prints,
# and the suite prints all of them on every run — so `bash pre-push.test.sh` is the current
# answer, while a hand-kept list is a second copy that nothing updates. This one had already
# gone stale twice: a miscounted grep call-site claim, then three cases missing outright.
#
# A synthetic term is used throughout — this suite contains no personal data.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/pre-push"

# Every scratch repo lives here and dies with the run. Git is isolated from the developer's and
# CI's own config so an inherited hooksPath, template dir, or signing key cannot change a result.
TEST_TMP="$(mktemp -d)"
trap 'chmod -R u+rwX "$TEST_TMP" 2>/dev/null; rm -rf "$TEST_TMP"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
# PII_DENYLIST is one of the hook's two denylist sources, and the activation route its own header
# documents first. run_hook calls `env` without -i, so an exported denylist would otherwise reach
# the hook and be UNIONED with the scratch repo's file — the file is still read and the synthetic
# term still matches, but the inherited terms ride along, so a test asserting a clean push passes
# or fails on whatever happens to be in the maintainer's own environment. CI sets no such variable,
# so this only bites someone running the suite locally — loudly, but pointlessly. (An earlier
# version of this comment said the file "would never be opened"; the hooks union, they do not
# replace, which is what the union case below asserts.)
# The two tests that need the variable inject it explicitly through run_hook.
unset PII_DENYLIST
# The hook's own staleness warning is about the developer's install, not about these scratch
# repos; individual staleness tests re-enable it.
export EXCOG_PREPUSH_NO_STALE_CHECK=1

TERM_STR="ACME-TESTPERSON"          # synthetic denylist term; never a real name
Z=0000000000000000000000000000000000000000

# Colors for output ($'...' form survives editor normalization that would
# strip raw ESC bytes from a regular single-quoted string).
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
NC=$'\033[0m' # No Color

PASSED=0
FAILED=0

pass() { PASSED=$((PASSED+1)); printf "${GREEN}PASS${NC}  %s\n" "$1"; }
fail() { FAILED=$((FAILED+1)); printf "${RED}FAIL${NC}  %s\n      %s\n" "$1" "$2"; }

# newrepo <name> — creates and enters a scratch repo with a one-term denylist.
# Must NOT be called inside $( ): the cd has to persist for the commits that follow.
newrepo() {
    R="$TEST_TMP/$1"
    mkdir -p "$R"
    cd "$R"
    git -c init.defaultBranch=main init -q .
    git config user.email test@example.invalid
    git config user.name "Test Runner"
    git config commit.gpgsign false
    # Without this, `git add .` commits the denylist itself and the hook matches its own patterns.
    printf 'pii-denylist.local\n' > "$R/.gitignore"
    printf '%s\n' "$TERM_STR" > "$R/pii-denylist.local"
}

# run_hook <repo> <remote-name> <stdin-line> [env-assignment ...] — sets RC and OUT.
run_hook() {
    local repo="$1" rem="$2" line="$3"
    shift 3
    set +e
    OUT="$(cd "$repo" && printf '%s\n' "$line" | env "$@" bash "$HOOK" "$rem" 2>&1)"
    RC=$?
    set -e
}

# A block is rc!=0 AND a BLOCKED message — rc alone could come from any other failure.
expect_block() {
    if [ "$RC" -ne 0 ] && printf '%s' "$OUT" | grep -q BLOCKED; then
        pass "$1"
    else
        fail "$1" "expected block; rc=$RC out=$(printf '%s' "$OUT" | head -1)"
    fi
}
expect_allow() {
    if [ "$RC" -eq 0 ] && ! printf '%s' "$OUT" | grep -q BLOCKED; then
        pass "$1"
    else
        fail "$1" "expected allow; rc=$RC out=$(printf '%s' "$OUT" | head -1)"
    fi
}
expect_out() {   # name, needle
    if printf '%s' "$OUT" | grep -q "$2"; then
        pass "$1"
    else
        fail "$1" "expected output to contain '$2'; got: $(printf '%s' "$OUT" | head -1)"
    fi
}
expect_not_out() {
    if printf '%s' "$OUT" | grep -q "$2"; then
        fail "$1" "output should not contain '$2'"
    else
        pass "$1"
    fi
}
# The denylisted term must never reach the terminal or a CI log.
expect_no_leak() {
    if printf '%s' "$OUT" | grep -qi "$TERM_STR"; then
        fail "$1" "denylisted term leaked into output"
    else
        pass "$1"
    fi
}

echo ""
echo -e "${YELLOW}--- Baseline and log safety ---${NC}"

newrepo baseline
echo clean > a.txt; git add .; git commit -qm c1
BASE=$(git rev-parse HEAD)
echo "written by $TERM_STR" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block   "name in outgoing commits blocks the push"
expect_no_leak "matched term is not echoed"

# The term in the commit MESSAGE rather than in any file. This is the most obvious leak vector of
# all and it was the one case the suite never asserted — it works because `git log -p` prints the
# message above the diff, which is exactly the kind of incidental coverage a later flag change can
# remove without any test going red.
newrepo commitmsg
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo y > b.txt; git add .; git commit -qm "thanks to $TERM_STR for the fix"
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block   "a name in a commit MESSAGE blocks"
expect_no_leak "the commit-message match is not echoed"

newrepo clean
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo y > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_allow "clean commits are allowed through"

newrepo refdelete
echo x > a.txt; git add .; git commit -qm c1
run_hook "$R" origin "refs/heads/gone $Z refs/heads/gone $(git rev-parse HEAD)"
expect_allow "a ref deletion is not scanned"

echo ""
echo -e "${YELLOW}--- Fail closed: a scan that could not run must never read as clean ---${NC}"

# git cannot resolve the range (the remote advertised a SHA this clone does not have — an
# ordinary force-push-after-someone-else-advanced-the-branch, with no intervening fetch).
newrepo gitfail
echo x > a.txt; git add .; git commit -qm c1
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
expect_block "an undeterminable push range blocks"

# An unreadable denylist is caught by the hook's own readability precheck, BEFORE grep runs — so
# this covers that precheck, not grep's error status. The grep-error branch is covered separately
# below, and the mktemp branch by `tmpfail`.
newrepo unreadable
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
chmod 000 "$R/pii-denylist.local"
if [ -r "$R/pii-denylist.local" ]; then
    # Running as root: chmod cannot make a file unreadable, so the case is unreachable here.
    printf "${YELLOW}SKIP${NC}  unreadable denylist blocks (running as root)\n"
else
    run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
    expect_block "an unreadable denylist blocks"
fi
chmod 644 "$R/pii-denylist.local"

# grep's OWN error status (>=2) must not be mistaken for its no-match status (1). Reaching that
# branch needs grep itself to fail while the denylist is readable, so a stub earlier on PATH fails
# only on the SECOND pattern-file call: the first is the hook's ref-name check, which must still
# succeed, and the second is the outgoing-commits scan, which must block.
newrepo greperror
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "nothing interesting" > b.txt; git add .; git commit -qm c2
mkdir -p "$R/stub"
cat > "$R/stub/grep" <<'STUB'
#!/bin/bash
for a in "$@"; do
  if [ "$a" = "-f" ]; then
    n=$(( $(cat "$STUB_COUNT" 2>/dev/null || echo 0) + 1 ))
    echo "$n" > "$STUB_COUNT"
    [ "$n" -ge 2 ] && exit 2
    break
  fi
done
for g in /usr/bin/grep /bin/grep; do [ -x "$g" ] && exec "$g" "$@"; done
exit 2
STUB
chmod +x "$R/stub/grep"
: > "$R/stub-count"
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE" \
    "PATH=$R/stub:$PATH" "STUB_COUNT=$R/stub-count"
expect_block "a grep that errors blocks instead of reading as clean"
expect_out   "the grep-error block names the scan failure" "scan itself failed"

# The same guarantee for the very first pattern-file call, which is the ref-name check.
: > "$R/stub-count"; echo 1 > "$R/stub-count"
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE" \
    "PATH=$R/stub:$PATH" "STUB_COUNT=$R/stub-count"
expect_block "a grep error during the ref-name check also blocks"

# A failed mktemp must not leave the gate silently disarmed. TMPDIR points at a non-writable path,
# so mktemp fails while a valid denylist is present — the hook must block, not report INACTIVE.
newrepo tmpfail
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE" \
    "TMPDIR=$R/definitely-not-a-writable-dir"
expect_block   "a failed mktemp blocks rather than reporting INACTIVE"
expect_not_out "a failed mktemp does not claim INACTIVE" "INACTIVE"

# mktemp SUCCEEDING is not the same guarantee: the writes INTO that file are what build the pattern
# list. If TMPDIR fills or remounts read-only after the temp file is named, `norm > "$DENY"` writes
# nothing, and an empty $DENY reads as "no terms" — an armed denylist silently downgraded to
# INACTIVE. A stub mktemp returns a path under a directory that does not exist, so mktemp exits 0
# and ONLY the redirection fails. Both sources get a case, because each has its own redirection.
newrepo denywrite
mkdir -p "$R/stub"
cat > "$R/stub/mktemp" <<STUB
#!/bin/bash
echo "$R/no-such-dir/deny.tmp"
STUB
chmod +x "$R/stub/mktemp"
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE" "PATH=$R/stub:$PATH"
expect_block   "an unwritable denylist temp file blocks (file source)"
expect_not_out "a failed denylist write does not claim INACTIVE" "INACTIVE"

run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE" \
    "PATH=$R/stub:$PATH" "PII_DENYLIST=$TERM_STR"
expect_block "an unwritable denylist temp file blocks (env source)"

# The same silent-INACTIVE outcome through a different door: norm's own `grep -v ... || true` turned
# a grep FAILURE into an empty $DENY. grep exits 1 when every line was a comment or a blank, which
# is legitimate and must still pass, so only >=2 may block.
newrepo normgreperr
mkdir -p "$R/stub"
cat > "$R/stub/grep" <<'STUB'
#!/bin/bash
for a in "$@"; do [ "$a" = "-v" ] && exit 2; done
for g in /usr/bin/grep /bin/grep; do [ -x "$g" ] && exec "$g" "$@"; done
exit 2
STUB
chmod +x "$R/stub/grep"
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE" "PATH=$R/stub:$PATH"
expect_block   "a grep error inside denylist normalization blocks"
expect_not_out "a normalization grep error does not claim INACTIVE" "INACTIVE"

echo ""
echo -e "${YELLOW}--- The denylist's own path is never echoed ---${NC}"

# The block messages name where the terms came from. While that was an absolute path, a clone living
# under a directory named after the person made the gate print the very term it withholds from the
# matched line and from the matching ref name.
newrepo "$TERM_STR-parent/repo"
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block   "a name in the commits still blocks from a term-named directory"
expect_no_leak "the block message does not echo the denylist's own path"

# The unreadable-denylist precheck printed the path outright, and cannot denylist-check it either —
# the denylist it would need is the file it just failed to read.
newrepo "$TERM_STR-parent2/repo"
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
chmod 000 "$R/pii-denylist.local"
if [ -r "$R/pii-denylist.local" ]; then
    printf "${YELLOW}SKIP${NC}  unreadable-denylist message does not echo its path (running as root)\n"
else
    run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
    expect_block   "an unreadable denylist in a term-named directory blocks"
    expect_no_leak "the unreadable-denylist message does not echo its path"
fi
chmod 644 "$R/pii-denylist.local"

echo ""
echo -e "${YELLOW}--- Content the scan used to miss ---${NC}"

# grep -I declares the WHOLE stream binary at the first NUL and abandons it. git log -p is
# reverse-chronological, so a NUL in a NEWER commit would hide a name in an older one.
newrepo nulbyte
echo x > a.txt; git add .; git commit -qm c0; BASE=$(git rev-parse HEAD)
echo "note about $TERM_STR" > notes.md; git add .; git commit -qm "adds the name"
{ head -c 9000 /dev/zero | tr '\0' 'a'; printf 'tail\0\0binary'; } > gen.log
git add .; git commit -qm "adds a file with a NUL byte"
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block "a NUL byte in another commit does not blind the scan"

# git log -p prints no diff body for a merge commit without -m.
newrepo mergecommit
echo base > f.txt; git add .; git commit -qm c0; BASE=$(git rev-parse HEAD)
git checkout -q -b side; echo side > f.txt; git commit -qam cs
git checkout -q -; echo main > f.txt; git commit -qam cm
git merge side -q >/dev/null 2>&1 || true
echo "resolved by $TERM_STR" > f.txt; git add f.txt; git commit -qm "merge resolve" >/dev/null
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block "a name added only in a merge resolution blocks"

# A tag object's message never appears in git log output.
newrepo tagmsg
echo x > a.txt; git add .; git commit -qm c1
git tag -a v1 -m "release by $TERM_STR"
run_hook "$R" origin "refs/tags/v1 $(git rev-parse v1) refs/tags/v1 $Z"
expect_block   "a name in an annotated tag message blocks"
expect_no_leak "tag-message match is not echoed"

# An object git cannot read is "could not check", not "not a tag". While the type probe ended in
# `|| true`, a failed cat-file produced an empty string, which simply is not "tag" — so the
# annotation scan was skipped in silence and only the commit scan ran.
#
# Asserting only "blocks" would NOT discriminate here, and that is worth spelling out: the old code
# also blocked this input, because the same missing object then failed `git log` and tripped the
# push-range guard. It reached the right outcome through a branch that says nothing about tags — so
# the assertion is on the tag-specific message, which is the only evidence the annotation path
# itself failed closed. Verified: the old hook passes the block check and fails this one.
newrepo tagunreadable
echo x > a.txt; git add .; git commit -qm c1
run_hook "$R" origin "refs/tags/v9 deadbeefdeadbeefdeadbeefdeadbeefdeadbeef refs/tags/v9 $Z"
expect_block "an unreadable tag object blocks instead of skipping the annotation scan"
expect_out   "the unreadable-tag block names the tag object, not the commit range" \
             "object for this tag could not be read"

# A path marked `-diff` in .gitattributes makes git print "Binary files ... differ" in place of the
# content, so the scan has nothing to match — and .gitattributes is IN the repo, so this needs no
# unusual local config to arrive. `--text` is what overrides it; --no-ext-diff/--no-textconv close
# the neighbouring config-driven routes (an external diff driver, a textconv filter).
newrepo binattr
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
printf 'notes.md -diff\n' > .gitattributes
echo "written by $TERM_STR" > notes.md
git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block "a path marked -diff in .gitattributes cannot hide a name"

# `git log`'s default format prints Author but NOT Commit, so a commit whose COMMITTER identity
# carries the name travels to the remote unscanned — and an amend or a rebase is exactly where the
# two identities diverge.
newrepo committerident
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo y > b.txt; git add .
GIT_COMMITTER_NAME="$TERM_STR" git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block   "a denylisted name in the COMMITTER identity blocks"
expect_no_leak "the committer-identity block does not echo the name"

echo ""
echo -e "${YELLOW}--- The all-zeros sentinel is hash-width agnostic ---${NC}"

# git pads the sentinel to the repo's hash width: 40 hex for SHA-1, 64 for SHA-256. Comparing
# against a hardcoded 40 zeros never matches in a SHA-256 repo, so a deletion is not recognized and
# a new branch builds its range from an object that does not exist. Both then block — fail-closed,
# so not a leak, but every push in such a repo is bricked.
Z64=0000000000000000000000000000000000000000000000000000000000000000
newrepo zerowidth
echo x > a.txt; git add .; git commit -qm c1
run_hook "$R" origin "refs/heads/gone $Z64 refs/heads/gone $(git rev-parse HEAD)"
expect_allow "a 64-zero deletion sentinel is recognized as a deletion"
run_hook "$R" origin "refs/heads/new $(git rev-parse HEAD) refs/heads/new $Z64"
expect_allow "a 64-zero new-branch sentinel scans rather than failing to resolve"

echo ""
echo -e "${YELLOW}--- Push-range scoping ---${NC}"

# Positional revs mean "reachable from", which would scan the whole history and block on terms
# already in pushed commits — telling the operator to rewrite published history.
newrepo rangescope
echo "old $TERM_STR" > old.txt; git add .; git commit -qm "already-pushed commit with the name"
PUSHED=$(git rev-parse HEAD)
echo newfile > new.txt; git add .; git commit -qm "clean new commit"
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $PUSHED"
expect_allow "already-pushed history is not re-scanned"

# A new branch on a SECOND remote: its commits are on origin but not on the target.
newrepo secondremote
echo "has $TERM_STR" > a.txt; git add .; git commit -qm "name commit"
SHA=$(git rev-parse HEAD)
git update-ref refs/remotes/origin/main "$SHA"      # already on origin
git remote add mirror /dev/null
run_hook "$R" mirror "refs/heads/main $SHA refs/heads/main $Z"
expect_block "pushing to a second remote scans commits already on origin"

# A remote-tracking ref is a CACHE of the last fetch, not remote truth. When it is STALE — the
# remote's branch was force-pushed away or deleted — excluding it dropped commits the remote does
# NOT have from the scan, and a name in one of them rode out on a new branch reporting ALLOWED.
newrepo staleref
BARE="$PWD/../staleref-origin.git"
rm -rf "$BARE"; git init -q --bare "$BARE"
git remote remove origin >/dev/null 2>&1 || true
git remote add origin "$BARE"
echo clean > a.txt; git add .; git commit -qm "clean base"
git push -q origin HEAD:refs/heads/main
git checkout -q -b feat2
echo "has $TERM_STR" > b.txt; git add .; git commit -qm "commit carrying the name"
# origin/old points at the name commit, but the remote has no such branch — never pushed there.
git update-ref refs/remotes/origin/old "$(git rev-parse HEAD)"
run_hook "$R" origin "refs/heads/feat2 $(git rev-parse HEAD) refs/heads/feat2 $Z"
expect_block "a stale remote-tracking ref does not exclude commits the remote does not have"

echo ""
echo -e "${YELLOW}--- Ref names ---${NC}"

newrepo refname
echo x > a.txt; git add .; git commit -qm c1
git checkout -q -b "feature/$TERM_STR-fixes"
run_hook "$R" origin "refs/heads/feature/$TERM_STR-fixes $(git rev-parse HEAD) refs/heads/feature/$TERM_STR-fixes $Z"
expect_block   "a denylisted term in the ref NAME blocks"
expect_no_leak "the offending ref name is not echoed"

echo ""
echo -e "${YELLOW}--- Denylist normalization ---${NC}"

newrepo crlf
printf '%s\r\n' "$TERM_STR" > "$R/pii-denylist.local"      # Windows-side editor under WSL
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR here" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block "a CRLF-saved denylist still matches"

newrepo pipesep
printf 'OTHER-TERM|%s\n' "$TERM_STR" > "$R/pii-denylist.local"   # the CI secret's own format
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block "a '|'-separated denylist file is normalized"

# A denylist kept as an indented list normalizes to a NON-EMPTY file, so the gate reports itself
# armed and names its source — while every pattern carries leading blanks that `grep -F` then
# requires literally, so it matches nothing. Armed-looking and inert is the worst of both states.
newrepo indented
printf '  %s\n' "$TERM_STR" > "$R/pii-denylist.local"
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR here" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block "an indented denylist entry still matches"

newrepo blankline
printf '\n%s\n\n' "$TERM_STR" > "$R/pii-denylist.local"
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "nothing to see" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_allow "a blank line is not an empty pattern that matches everything"

newrepo commentsonly
printf '# add names below\n\n' > "$R/pii-denylist.local"
echo x > a.txt; git add .; git commit -qm c1
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $Z"
expect_out "a comments-only denylist reports itself INACTIVE" "INACTIVE"

# .gitignore has always ignored pii-denylist.txt as well, but only pii-denylist.local was ever read
# — so a contributor who followed the ignore hint saw their file correctly ignored and believed the
# gate was armed. Honoring both names is the fail-safe direction; dropping the ignore entry instead
# would leave a file full of real names committable.
newrepo altname
mv "$R/pii-denylist.local" "$R/pii-denylist.txt"
printf 'pii-denylist.local\npii-denylist.txt\n' > "$R/.gitignore"
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE"
expect_block "a denylist named pii-denylist.txt is honored too"

newrepo envmask
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE" "PII_DENYLIST=|"
expect_block "an empty PII_DENYLIST does not mask a valid local denylist"

newrepo envwins
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has OTHER-ENV-TERM" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE" "PII_DENYLIST=OTHER-ENV-TERM"
expect_block "PII_DENYLIST terms are used when set"

# UNION, not precedence: with the env var set, the local file's terms must STILL match. Under the
# old fallback semantics the env var replaced the file, so exporting PII_DENYLIST silently dropped
# every term in the operator's own denylist — this commit contains only a file term, and the env
# var is set to a term it does not contain.
newrepo envunion
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $BASE" "PII_DENYLIST=OTHER-ENV-TERM"
expect_block "the local file's terms still match when PII_DENYLIST is set (union, not replace)"

echo ""
echo -e "${YELLOW}--- Linked worktrees ---${NC}"

# The denylist is gitignored and untracked, so it does not exist at a linked worktree's own root;
# resolving only --show-toplevel there would silently report the guard INACTIVE.
newrepo worktree
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
git worktree add -q "$TEST_TMP/wt-linked" -b feat >/dev/null 2>&1
run_hook "$TEST_TMP/wt-linked" origin "refs/heads/feat $(git -C "$TEST_TMP/wt-linked" rev-parse HEAD) refs/heads/feat $BASE"
expect_block "a linked worktree finds the main clone's denylist"

echo ""
echo -e "${YELLOW}--- Bare repositories ---${NC}"

# A bare repo has NO work tree, so --show-toplevel is empty and the common git dir IS the repo.
# Taking only that dir's PARENT therefore looked in whatever unrelated directory happens to contain
# the repo. Measured before the fix: a denylist in the bare repo's own root was never found, the
# hook announced itself INACTIVE, and a commit carrying the term was allowed out.
newrepo baresrc
echo x > a.txt; git add .; git commit -qm c1; BASE=$(git rev-parse HEAD)
echo "has $TERM_STR" > b.txt; git add .; git commit -qm c2
SHA=$(git rev-parse HEAD)
git clone -q --bare "$R" "$TEST_TMP/bare-target.git"
# The parent dir deliberately holds NO denylist, so only the bare root's own file can satisfy this.
printf '%s\n' "$TERM_STR" > "$TEST_TMP/bare-target.git/pii-denylist.local"
run_hook "$TEST_TMP/bare-target.git" origin "refs/heads/main $SHA refs/heads/main $BASE"
expect_block   "a bare repo finds the denylist in its own root"
expect_not_out "a bare repo does not report the gate INACTIVE" "INACTIVE"

echo ""
echo -e "${YELLOW}--- Staleness of a cp-installed copy ---${NC}"

# A private copy under .git/hooks/ is never updated by a pull. The running script is compared
# against the repo's tracked .githooks/pre-push, so drift is reported rather than silent.
newrepo stale
mkdir -p "$R/.githooks"
printf '#!/usr/bin/env bash\n# a DIFFERENT (older) tracked hook\nexit 0\n' > "$R/.githooks/pre-push"
echo x > a.txt; git add .; git commit -qm c1
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $Z" "EXCOG_PREPUSH_NO_STALE_CHECK="
expect_out "a drifted private copy warns" "WARNING"

newrepo notstale
mkdir -p "$R/.githooks"
cp "$HOOK" "$R/.githooks/pre-push"
echo x > a.txt; git add .; git commit -qm c1
run_hook "$R" origin "refs/heads/main $(git rev-parse HEAD) refs/heads/main $Z" "EXCOG_PREPUSH_NO_STALE_CHECK="
expect_not_out "an up-to-date copy does not warn" "WARNING"

echo ""
echo ""

# ============================================================
# Results
# ============================================================
echo "====================================="
echo -e "Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
echo ""

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
