#!/bin/sh
# Merge V1 into imrul-deploy whenever V1 is pushed from this machine.
#
# Production (Imrul's server) builds the imrul-deploy branch, which is V1 plus
# the server's Docker/deploy files. This keeps it current without anyone having
# to remember the merge. Called by .git/hooks/pre-push with git's pre-push
# stdin (one "<local ref> <local sha> <remote ref> <remote sha>" line per ref).
#
# It never blocks the V1 push: if the imrul-deploy worktree has uncommitted
# changes, or the merge conflicts, it backs out and prints what to do.
# The .github/workflows/sync-imrul-deploy.yml Action does the same on GitHub
# for pushes made elsewhere.

[ -n "$GM_SYNC_RUNNING" ] && exit 0   # the nested push below

v1_sha=""
while read -r local_ref local_sha remote_ref remote_sha; do
  if [ "$remote_ref" = "refs/heads/V1" ] && [ "$local_sha" != "0000000000000000000000000000000000000000" ]; then
    v1_sha="$local_sha"
  fi
done
[ -z "$v1_sha" ] && exit 0

say() { echo "[sync-imrul-deploy] $*" >&2; }

wt=$(git worktree list --porcelain | awk '/^worktree /{w=substr($0,10)} /^branch refs\/heads\/imrul-deploy$/{print w}')
if [ -z "$wt" ]; then
  say "no worktree has imrul-deploy checked out; skipped. Merge by hand: git checkout imrul-deploy && git merge V1"
  exit 0
fi
if [ -n "$(git -C "$wt" status --porcelain --untracked-files=no)" ]; then
  say "$wt has uncommitted changes; skipped so nothing of Imrul's is touched. Commit or stash there, then: git -C \"$wt\" merge V1 && git -C \"$wt\" push origin imrul-deploy"
  exit 0
fi
if git -C "$wt" merge-base --is-ancestor "$v1_sha" HEAD; then
  exit 0   # already merged
fi

git -C "$wt" fetch -q origin imrul-deploy 2>/dev/null && git -C "$wt" merge -q --ff-only origin/imrul-deploy 2>/dev/null
if ! git -C "$wt" merge -q --no-ff --no-edit -m "Merge V1 into imrul-deploy (automatic)" "$v1_sha"; then
  git -C "$wt" merge --abort 2>/dev/null
  say "merge conflict; nothing changed. Resolve it by hand in $wt: git merge V1"
  exit 0
fi
if GM_SYNC_RUNNING=1 git -C "$wt" push -q origin imrul-deploy; then
  say "merged V1 ($(echo "$v1_sha" | cut -c1-9)) into imrul-deploy and pushed it."
else
  say "merged locally but the imrul-deploy push failed; run: git -C \"$wt\" push origin imrul-deploy"
fi
exit 0
