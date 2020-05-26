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

set -e
# Ensure we're in the correct directory
declare BASE="$(git rev-parse --show-toplevel)"
[[ "$(pwd)" != "${BASE}" ]] && cd "${BASE}"

die() {
  echo -e "$2" >&2
  exit $1
}


# nose2 --fail-fast \
#       --with-coverage --coverage-report=term-missing \
#       --verbose



# Why coverage and not nose2-cov? We are using the coverage module to invoke test runner (nose2) rather than using a plugin for test runner to report coverage (nose2-cov), because nose-2 cov doesnt seem to have a --fail-under option.   https://stackoverflow.com/questions/52205363/have-nosetests-ignore-minimum-coverage-if-exit-due-to-test-failure


coverage run -m nose2 --fail-fast  --coverage-report=term-missing \
   --verbose

coverage report --rcfile=.hotCoveragerc  || die 1 "Hot Coverage is not satisfied"
coverage report --rcfile=.warmCoveragerc || die 1 "Warm Coverage is not satisfied"
coverage report --rcfile=.coldCoveragerc || die 1 "Cold Coverage is not satisfied"






# radon cc -s --total-average -nb -j --json hot/

# must conform to the PEP8 style: Pylint is a Python static code analysis tool which looks for programming errors, helps enforcing a coding standard, sniffs for code smells and offers simple refactoring suggestions.

# Mypy: The system's code must be fully type annotated and satisfy static analysis.
