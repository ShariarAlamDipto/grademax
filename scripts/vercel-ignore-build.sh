#!/bin/bash
# Vercel "Ignored Build Step" (vercel.json ignoreCommand).
# Exit 0 = skip this build, exit 1 = build.
#
# Every build is a fresh deployment: it adds ~100 MB to Deployment Storage and
# throws away the ISR cache, so the ~10k on-demand past-paper pages (mostly
# Cambridge leaves) all render and write again on their next visit. Most commits
# only touch the offline pipeline, which the website never reads, so those
# builds bought nothing.
#
# Fails safe: anything unexpected (no previous SHA, shallow clone missing it,
# any file outside the skip list) builds.

# Only production deploys. Branch-agnostic on purpose: whichever branch Vercel
# treats as production keeps building; pushes to other branches stop creating
# Preview deployments.
if [ "$VERCEL_ENV" != "production" ]; then
  echo "Skipping: $VERCEL_ENV build (only production builds)."
  exit 0
fi

if [ -z "$VERCEL_GIT_PREVIOUS_SHA" ]; then
  echo "Building: no previous deployment SHA to diff against."
  exit 1
fi

changed=$(git diff --name-only "$VERCEL_GIT_PREVIOUS_SHA" HEAD 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "Building: could not diff against $VERCEL_GIT_PREVIOUS_SHA."
  exit 1
fi

# An empty diff is a deliberate redeploy (the empty "trigger production deploy"
# commit used to get around Vercel's same-SHA dedupe), so it must build.
if [ -z "$changed" ]; then
  echo "Building: empty diff, treating as a deliberate redeploy."
  exit 1
fi

# Paths the website build never reads. scripts/generate-papers-index.mjs runs
# as prebuild, so it is the one script that must still trigger a build.
site_changes=$(echo "$changed" | grep -vE \
  -e '^(data|ingest|supabase|migrations|db|classification|config|docs|training-data|logs|output|tests)/' \
  -e '^scripts/' \
  -e '^[^/]+\.(md|sql|py|txt|ps1|bat)$' \
  -e '^$')
if echo "$changed" | grep -q '^scripts/generate-papers-index\.mjs$'; then
  site_changes="$site_changes scripts/generate-papers-index.mjs"
fi

if [ -z "$(echo "$site_changes" | tr -d '[:space:]')" ]; then
  echo "Skipping: only pipeline/data files changed."
  exit 0
fi

echo "Building: website files changed:"
echo "$site_changes" | head -20
exit 1
