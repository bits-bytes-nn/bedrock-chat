#!/usr/bin/env bash
# docker build that retries only when ECR Public rate-limits the anonymous pulls of
# shared CI runners (429). Any other failure fails at once.
set -uo pipefail

log=$(mktemp)
for attempt in 1 2 3; do
  if docker build "$@" 2>&1 | tee "$log"; then
    exit 0
  fi
  if ! grep -q "429 Too Many Requests" "$log"; then
    exit 1
  fi
  echo "ECR Public rate limit, retrying in $((attempt * 60)) seconds" >&2
  sleep $((attempt * 60))
done
exit 1
