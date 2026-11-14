#!/usr/bin/env bash
# Runs a command that pulls from ECR Public (docker build, CDK bundling) and retries
# it only when ECR Public rate-limits the anonymous pulls of shared CI runners (429).
# Any other failure fails at once.
set -uo pipefail

log=$(mktemp)
trap 'rm -f "$log"' EXIT
attempts=3
for attempt in $(seq "$attempts"); do
  "$@" 2>&1 | tee "$log"
  status=${PIPESTATUS[0]}
  if [ "$status" -eq 0 ]; then
    exit 0
  fi
  if [ "$attempt" -eq "$attempts" ] ||
    ! grep -Eq "429 Too Many Requests|toomanyrequests" "$log"; then
    exit "$status"
  fi
  echo "ECR Public rate limit, retrying in $((attempt * 60)) seconds" >&2
  sleep $((attempt * 60))
done
