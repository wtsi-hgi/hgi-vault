#!/usr/bin/env bash

declare BASE="$(git rev-parse --show-toplevel)"
declare HOOK_DIR=".ci/git-hooks"

declare HOOK_PATH
declare HOOK
while read -r HOOK_PATH; do
  HOOK="$(basename "${HOOK_PATH}")"
  ln -f "${HOOK_PATH}" "${BASE}/.git/hooks/${HOOK}"
  echo "Installed ${HOOK}"
done < <(find "${BASE}/${HOOK_DIR}" -type f 2>/dev/null)

echo "Done"
