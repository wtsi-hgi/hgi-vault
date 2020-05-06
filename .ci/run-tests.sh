#!/usr/bin/env bash

# TODO Test Runner
#
# * Run tests (exit non-zero on failure)
#
# * Establish hot, warm and cool code (hot is anything in hot/, warm is
#   anything referenced by hot, cool is everything else)
#
#   * Hot code must have: Coverage = 100%; McCabe <= 5
#   * Warm code must have: Coverage > 90%; McCabe <= 5
#   * Cool code must have: Coverage > 80%; McCabe <= 10 (warn if > 7)
#
#   Anything not satisfying the above should exit non-zero
#
# * PEP8 and type checking (maybe warn, rather than fail, because of
#   false positives)

# Ensure we're in the correct directory
declare BASE="$(git rev-parse --show-toplevel)"
[[ "$(pwd)" != "${BASE}" ]] && cd "${BASE}"

nose2 --fail-fast \
      --with-coverage --coverage-report=term-missing \
      --verbose
