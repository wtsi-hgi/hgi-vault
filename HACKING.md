# Developer Documentation

Please ensure you familiarise yourself with the [design
constraints](doc/design.md) before contributing.

## Git Setup

Clone this repository from GitHub:

    git clone https://github.com/wtsi-hgi/hgi-vault.git

All development must be in the `develop` branch and, preferably, in
feature/fix branches (as required).

From the repository root, set the Git commit template with:

    git config commit.template $(pwd)/.ci/commit.template

...and install Git hooks with:

    .ci/install-hooks.sh

## Python Virtual Environment

You will need to create and activate a Python 3.7 (or newer) virtual
environment. For example:

    python -m venv .venv
    source .venv/bin/activate

Once activated, the project's requirements and testing requirements can
be installed with:

    pip install -r .ci/test-requirements.txt \
                -r requirements.txt

## Manually Running the Test Suite

With the virtual environment activated:

    .ci/run-tests.sh

## Legal Boilerplate

All non-trivial source files must begin with the following, as a
comment:

> Copyright (c) **YEAR(S)** **HOLDER**
>
> Author: **AUTHOR(S)**
>
> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
> the Free Software Foundation, either version 3 of the License, or (at
> your option) any later version.
>
> This program is distributed in the hope that it will be useful, but
> WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
> General Public License for more details.
>
> You should have received a copy of the GNU General Public License
> along with this program. If not, see https://www.gnu.org/licenses/

Where:

* **YEAR(S)** are the years in which significant changes have been
  made to the file. A span of consecutive years may be elided with a
  hyphen.

* **HOLDER** is the copyright holder. For Sanger Institute staff, this
  must be "Genome Research Limited".

* **AUTHOR(S)** is the list of authors, one per line, with their full
  name and e-mail address.
