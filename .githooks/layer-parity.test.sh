#!/usr/bin/env bash
# layer-parity.test.sh — fails when the gate's layers drift apart.
#
# WHY THIS FILE EXISTS. A review of this gate returned four findings, and every one of them was the
# same defect wearing a different hat: a component was hardened and its sibling was not, so the two
# stopped agreeing. The secret-overwrite tool searched two directories while pre-push searched
# three. pre-commit
# scanned without the flags that stop a `.gitattributes` line from blanking the diff. .gitignore
# covered one of the two filenames the hooks accept. None of these was a flaw in any component's own
# logic, and none of them was findable by testing a component on its own.
#
# The reason the drift happened is that nothing was checking. Each layer was hardened by hand, so
# parity survived only as long as whoever edited one remembered to edit the others — and that memory
# is exactly what a repo does not have. This file is the thing that remembers.
#
# The checks DERIVE from .githooks/pre-push wherever they can, instead of restating its rules. That
# distinction is the whole point: a check that hard-codes "the two filenames are .local and .txt" is
# a third copy of the rule and drifts like the first two. A check that reads the filenames out of
# pre-push cannot disagree with pre-push — it can only report that somebody else does.
#
# Run: bash .githooks/layer-parity.test.sh   (also runs in CI; see pii-denylist-guard.yml)
set -uo pipefail
cd "$(dirname "$0")/.." || { echo "cannot reach the repo root"; exit 1; }

G=0
GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YEL=$'\033[0;33m'; NC=$'\033[0m'
chk() { # description, status
  if [ "$2" -eq 0 ]; then printf '  %sPASS%s  %s\n' "$GREEN" "$NC" "$1"
  else printf '  %sFAIL%s  %s\n' "$RED" "$NC" "$1"; G=1; fi
}

PP=.githooks/pre-push
PC=.githooks/pre-commit
SD=.githooks/overwrite-ci-denylist
WF=.github/workflows/pii-denylist-guard.yml
GI=.gitignore
for f in "$PP" "$PC" "$SD" "$WF" "$GI"; do
  [ -f "$f" ] || { echo "missing $f — the gate is incomplete, not merely drifted"; exit 1; }
done

echo "${YEL}--- Denylist discovery: every layer must look in the same places ---${NC}"

# The filename list is READ OUT of pre-push, so adding a third name there automatically obliges
# .gitignore and overwrite-ci-denylist to follow, without anyone editing this file.
NAMES="$(sed -n 's/^[[:space:]]*for n in \(.*\); do$/\1/p' "$PP" | head -1)"
[ -n "$NAMES" ] || { echo "could not read the filename list out of $PP — has its search loop changed shape?"; exit 1; }

for n in $NAMES; do
  grep -qx -- "$n" "$GI"
  chk ".gitignore ignores $n, which pre-push accepts" $?
done

for n in $NAMES; do
  grep -q -- "$n" "$SD"
  chk "overwrite-ci-denylist looks for $n too (else the hooks scan a file the overwrite never writes)" $?
done

# Bare repos: $TOP is empty and the common dir IS the repo, so a layer that omits COMMON_DIR cannot
# find a denylist sitting in a bare repo's own root. pre-push fixed that; the siblings must match.
# The status is CAPTURED before chk's arguments expand: a $(command substitution) inside an
# argument runs during expansion and REPLACES $?, so `chk "$(basename ...)" $?` graded the
# basename, not the grep — every such check passed unconditionally. Found by sabotage, not by
# reading: the broken form looks identical to a working one and greens forever.
for f in "$PP" "$PC" "$SD"; do
  grep -q 'COMMON_DIR' "$f"; st=$?
  chk "$(basename "$f") searches the git common dir (bare-repo case)" "$st"
done

echo ""
echo "${YEL}--- Scan flags: what git is asked to EMIT ---${NC}"

# Each of these stops a repo-local setting from blanking the diff before grep ever sees it. Absent
# them, a scan is honestly clean about content it was never shown.
for flag in --text --no-ext-diff --no-textconv; do
  grep -q -- "$flag" "$PP"; a=$?
  grep -q -- "$flag" "$PC"; b=$?
  chk "pre-commit and pre-push both pass $flag" $(( a | b ))
done

echo ""
echo "${YEL}--- Normalization: one denylist must not behave as three ---${NC}"

# Held in variables, not temp files. A checker that needs a writable TMPDIR can report drift that
# does not exist the moment it runs somewhere read-only — which is exactly what it did on first
# run here. A parity check whose own failure mode is indistinguishable from the failure it reports
# is worse than no check, so it is written to need nothing but the two files it compares.
PP_NORM="$(awk '/^norm\(\) \{/,/^\}/' "$PP")"
PC_NORM="$(awk '/^norm\(\) \{/,/^\}/' "$PC")"
[ -n "$PP_NORM" ] && [ -n "$PC_NORM" ]
chk "both hooks define norm()" $?
[ "$PP_NORM" = "$PC_NORM" ]
chk "norm() is byte-identical in pre-commit and pre-push" $?

# Both hooks must UNION the env var with the file (appending file terms into the same pattern
# file), not let one source shadow the other. When they diverged from this, exporting
# PII_DENYLIST silently dropped every term in the operator's own local denylist.
for f in "$PP" "$PC"; do
  grep -qF 'norm < "$FILE_SRC" >> "$DENY"' "$f"; st=$?
  chk "$(basename "$f") UNIONS the env var with the local file (appends, does not replace)" "$st"
done

echo ""
echo "${YEL}--- The CI secret is written by the operator, never by a hook ---${NC}"

# The secret is write-only: an overwrite destroys a value nobody can read back. So the overwrite
# lives in a manual, typed-confirmation tool, and pre-push may only WARN about drift. A hook that
# regrew a call to the overwrite tool would silently re-create the automatic destruction.
# The tool's name may appear in pre-push only on comment and echo lines — any other line
# mentioning it is code that reaches it.
! grep -E '(sync-denylist|overwrite-ci-denylist)' "$PP" | grep -vE '^[[:space:]]*(#|echo)' | grep -q .
chk "pre-push never EXECUTES the secret-overwrite tool (it may only name it in messages)" $?
grep -qF '.pii-denylist.synced' "$PP"
chk "pre-push reads the sync marker, so it can warn when CI's terms have drifted" $?
grep -qF 'read -r reply' "$SD" && grep -qF '"$reply" != "Yes"' "$SD"
chk "overwrite-ci-denylist requires a typed Yes before touching the secret" $?

echo ""
echo "${YEL}--- Word-boundary matching: the layers must agree on what counts as a hit ---${NC}"

# Stated as an absence, deliberately: any content scan reaching the denylist WITHOUT -w is the
# failure. Counting occurrences would pass the moment someone adds a fourth scan and forgets.
! grep -q 'grep -a -i -F -f "\$DENY"' "$PP"
chk "no pre-push scan reaches the denylist without -w" $?
! grep -q 'grep -a -i -F -f "\$DENY"' "$PC"
chk "no pre-commit scan reaches the denylist without -w" $?
grep -q 'git grep -a -l -i -F -w -f' "$WF"
chk "the CI content scan uses -w, like the hooks" $?

# The CI *path* scan used to be a recorded exception: a substring match, so that `<name>scan.png`
# was caught. It now uses -w like everything else. Short terms were failing CI on unrelated paths,
# and a check that fails on everything gets ignored. The hooks already see paths whole-word, in the
# `+++ b/<path>` headers they scan. Stated as an absence, for the same reason as the hook checks
# above: any path scan that reaches the denylist without -w is the failure.
grep -q "git ls-files -z" "$WF" && grep -q 'grep -z -i -F -w -f' "$WF" && ! grep -q 'grep -z -i -F -f' "$WF"
chk "the CI path scan uses -w, like the content scans and the hooks" $?

echo ""
echo "${YEL}--- Secret exposure: only default-branch runs may name the secret's environment ---${NC}"

# The denylist secret is scoped to the `pii-denylist` environment so that a branch, which runs its
# own copy of this workflow, cannot read it. A later edit could undo that in two ways:
#  - a scanning job stops naming the environment. It then falls back to a repo-level secret that
#    every branch can read, or, on the default branch, to no secret at all, and scans nothing;
#  - a job names it UNCONDITIONALLY. Every branch push is then refused, and the check stays red.
# The count is taken against the jobs that read the secret, so a third such job added later has to
# follow the same rule.
N_SECRET_JOBS="$(grep -c 'DENYLIST: \${{ secrets.PII_DENYLIST }}' "$WF")"
N_COND_ENV="$(grep -cF "name: \${{ github.ref == format('refs/heads/{0}', github.event.repository.default_branch) && 'pii-denylist' || '' }}" "$WF")"
[ "$N_SECRET_JOBS" -ge 2 ] && [ "$N_COND_ENV" -eq "$N_SECRET_JOBS" ]
chk "every job reading PII_DENYLIST names pii-denylist only on default-branch runs ($N_COND_ENV of $N_SECRET_JOBS)" $?
# Any non-comment `environment:`/`name:` line that mentions pii-denylist, other than the guarded
# expression itself, is a naming of the environment. That covers trailing comments, quoting and the
# `environment: { name: ... }` flow form, which an exact-line match would miss.
! grep -E "^[[:space:]]*[^#[:space:]].*(environment|name):[^#]*pii-denylist|^[[:space:]]*(environment|name):[^#]*pii-denylist" "$WF" \
  | grep -vF "default_branch) && 'pii-denylist' || '' }}" | grep -q .
chk "no job names pii-denylist unconditionally (GitHub would refuse it on every branch push)" $?

echo ""
echo "${YEL}--- Coverage: something other than a hook must see history ---${NC}"

# Not a consistency check but a COVERAGE one, and it belongs here because the failure it guards is
# the same shape: a layer quietly missing rather than quietly disagreeing. The hooks are the only
# thing that prevents, and they are armed per clone by a command a contributor can simply never run.
# Without a history job in CI, such a clone has no history coverage at all — and a tree scan reports
# clean on a branch where a name was added and then removed, because the tree is genuinely clean.
grep -q '^  history:' "$WF"
chk "CI scans full history, not only the tree (covers a clone with no hooks installed)" $?

# Both CI scanning jobs must normalize identically to norm(); the CR strip appears once per job.
# -F is load-bearing: as a regex, \r is just an escaped r and matches the letter, not a backslash,
# so the pattern silently never matches and the check reports drift that does not exist. It did
# exactly that on its first run. A checker that cries wolf is a checker that gets ignored, which
# is a slower version of not having one.
[ "$(grep -cF "tr -d '\r'" "$WF")" -ge 2 ]
chk "the history job normalizes the denylist like the tree job does" $?

echo ""
echo "${YEL}--- NUL safety: a path may legally contain a newline ---${NC}"
grep -q "git ls-files -z" "$WF" && grep -q 'grep -z -i -F' "$WF"
chk "the path scan keeps NUL separation from ls-files through grep" $?

echo ""
echo "====================================="
if [ "$G" -eq 0 ]; then
  printf '%sThe gate'"'"'s layers agree.%s\n' "$GREEN" "$NC"
else
  printf '%sLAYER DRIFT — a component was changed and a sibling was not.%s\n' "$RED" "$NC"
  echo "Fix the sibling, or if the divergence is intentional, record it here as a named exception"
  echo "so the next reader learns it was chosen rather than forgotten."
fi
exit "$G"
