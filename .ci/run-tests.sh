#!/usr/bin/env bash



set -e
# Ensure we're in the correct directory
declare BASE="$(git rev-parse --show-toplevel)"
[[ "$(pwd)" != "${BASE}" ]] && cd "${BASE}"

# Function called whwenever exiting early. The first argument is the exit code and second argument is the error message to spit out. 
die() {
  echo -e "$2" >&2
  exit $1
}



# * Run tests (exit non-zero on failure)
coverage run -m nose2 --fail-fast  --coverage-report=term-missing \
   --verbose

# Earlier command (without coverage package) (Remove if not necessary):
# nose2 --fail-fast \
#       --with-coverage --coverage-report=term-missing --coverage-config="${BASE}/.ci/.coveragerc" \
#       --verbose

# * Establish hot, warm and cool code (hot is anything in hot/, warm is
#   anything referenced by hot, cool is everything else)

#   The following code checks that coverage thresholds are met

# * Hot code must have: Coverage = 100%
#   * Warm code must have: Coverage > 90%
#   * Cool code must have: Coverage > 80%
#
#   Anything not satisfying the above should exit non-zero

coverage report --rcfile=.hotCoveragerc  || die 1 "Hot Coverage is not satisfied"
coverage report --rcfile=.warmCoveragerc || die 1 "Warm Coverage is not satisfied"
coverage report --rcfile=.coldCoveragerc || die 1 "Cold Coverage is not satisfied"



# The following code checks that cyclomatic complexity ceiling is not exceeded.
#   * Hot code must have:  McCabe <= 5
#   * Warm code must have:  McCabe <= 5
#   * Cool code must have: McCabe <= 10 (warn if > 7)
#
#   Anything not satisfying the above should exit non-zero

# Controlled by conifuration file radon.cfg. The output can be parsed to do selective analysis on hot, warm and cold file paths. 

radon cc -s --total-average  -j --json -O cyclomatic_analysis *


# Must conform to the PEP8 style: Pylint is a Python static code analysis tool which looks for programming errors, helps enforcing a coding standard, sniffs for code smells and offers simple refactoring suggestions.

# Controlled by conifuration file .pylintrc
pylint --rcfile=.pylintrc *


# Mypy: The system's code must be fully type annotated and satisfy static analysis.


mypy hot core models --follow-imports=silent || die 1 "Failed Static Type Analysis "
